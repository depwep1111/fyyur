# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from forms import *
from sqlalchemy import or_

# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#


class Show(db.Model):
    __tablename__ = 'Shows'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'))
    start_time = db.Column(db.DateTime, nullable=False)


class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String)

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value.strftime("%Y-%m-%d %H:%M:%S"))
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime

# ----------------------------------------------------------------------------#
# Model response for some APIs.
# ----------------------------------------------------------------------------#


class ShowInfo:
    def __init__(self, id, name, num_upcoming_shows):
        self.id = id
        self.name = name
        self.num_upcoming_shows = num_upcoming_shows


class VenueData:
    def __init__(self, city, state, venues):
        self.city = city
        self.state = state
        self.venues = venues


class DataSearch:
    def __init__(self, count, data):
        self.count = count
        self.data = data

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    list_data = []
    # Group city and state of Venue
    data = Venue.query.with_entities(Venue.city, Venue.state).group_by(Venue.city, Venue.state).all()
    for info in data:
        list_venue_show = []
        # List corresponding venue with each city and state
        venues = Venue.query.with_entities(Venue.id, Venue.name) \
            .filter(Venue.city == info.city, Venue.state == info.state) \
            .all()
        for ve in venues:
            # Count number of coming shows
            num_upcoming_shows = Show.query.with_entities() \
                .add_columns(db.func.count(Show.venue_id).label('num_upcoming_shows')) \
                .filter(Show.venue_id == ve.id, Show.start_time > datetime.now()) \
                .group_by(Show.venue_id) \
                .all()
            venue_show = ShowInfo(ve.id, ve.name,
                                  0 if num_upcoming_shows == [] else num_upcoming_shows[0].num_upcoming_shows)
            list_venue_show.append(venue_show.__dict__)
        venue_data = VenueData(info.city, info.state, list_venue_show)
        list_data.append(venue_data.__dict__)
    return render_template('pages/venues.html', areas=list_data);


@app.route('/venues/search', methods=['POST'])
def search_venues():
    list_venue_show = []
    search_keyword = "%{}%".format(request.form['search_term'])
    list_venue = Venue.query.with_entities(Venue.id, Venue.name) \
        .filter(or_(Venue.name.ilike(search_keyword),
                    db.func.concat(Venue.city, ', ', Venue.state).ilike(search_keyword))) \
        .all()
    for ve in list_venue:
        num_upcoming_shows = Show.query.with_entities() \
            .add_columns(db.func.count(Show.venue_id).label('num_upcoming_shows')) \
            .filter(Show.venue_id == ve.id, Show.start_time > datetime.now()) \
            .group_by(Show.venue_id) \
            .all()
        venue_show = ShowInfo(ve.id, ve.name,
                              0 if num_upcoming_shows == [] else num_upcoming_shows[0].num_upcoming_shows)
        list_venue_show.append(venue_show.__dict__)
    response = DataSearch(len(list_venue_show), list_venue_show)
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    data = Venue.query.get(venue_id)
    past_shows = Show.query.join(Artist, Artist.id == Show.artist_id)\
        .add_columns(Artist.id.label('artist_id'),
                     Artist.name.label('artist_name'),
                     Artist.image_link.label('artist_image_link'),
                     Show.start_time.label('start_time'))\
        .filter(Show.venue_id == venue_id, Show.start_time <= datetime.now()).all()
    upcoming_shows = Show.query.join(Artist, Artist.id == Show.artist_id) \
        .add_columns(Artist.id.label('artist_id'),
                     Artist.name.label('artist_name'),
                     Artist.image_link.label('artist_image_link'),
                     Show.start_time.label('start_time')) \
        .filter(Show.venue_id == venue_id, Show.start_time > datetime.now()).all()
    if data is not None:
        data.past_shows = past_shows
        data.past_shows_count = len(past_shows)
        data.upcoming_shows = upcoming_shows
        data.upcoming_shows_count = len(upcoming_shows)

    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    error = False
    try:
        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        address = request.form['address']
        phone = request.form['phone']
        genres = ','.join(request.form.getlist('genres'))
        facebook_link = request.form['facebook_link']
        image_link = request.form['image_link']
        website = request.form['website_link']
        seeking_talent = (request.form.get('seeking_talent') is not None) & ('y' == request.form.get('seeking_talent'))
        seeking_description = request.form['seeking_description']
        venue = Venue(name=name, city=city, state=state, address=address, phone=phone, genres=genres,
                      facebook_link=facebook_link, image_link=image_link, website=website,
                      seeking_talent=seeking_talent, seeking_description=seeking_description)
        db.session.add(venue)
        db.session.commit()
    except():
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + venue.name + ' could not be listed.')
    else:
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
    except():
        db.session.rollback()
    finally:
        db.session.close()
    return render_template('pages/home.html')


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.with_entities(Artist.id, Artist.name).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    list_artist_show = []
    search_keyword = "%{}%".format(request.form['search_term'])
    list_artist = Artist.query.with_entities(Artist.id, Artist.name) \
        .filter(or_(Artist.name.ilike(search_keyword),
                    db.func.concat(Artist.city, ', ', Artist.state).ilike(search_keyword))) \
    .all()
    for ar in list_artist:
        num_upcoming_shows = Show.query.with_entities() \
            .add_columns(db.func.count(Show.artist_id).label('num_upcoming_shows')) \
            .filter(Show.artist_id == ar.id, Show.start_time > datetime.now()) \
            .group_by(Show.artist_id) \
            .all()
        artist_show = ShowInfo(ar.id, ar.name,
                               0 if num_upcoming_shows == [] else num_upcoming_shows[0].num_upcoming_shows)
        list_artist_show.append(artist_show.__dict__)
    response = DataSearch(len(list_artist_show), list_artist_show)
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    data = Artist.query.get(artist_id)

    past_shows = Show.query.join(Venue, Venue.id == Show.venue_id) \
        .add_columns(Venue.id.label('venue_id'),
                     Venue.name.label('venue_name'),
                     Venue.image_link.label('venue_image_link'),
                     Show.start_time.label('start_time')) \
        .filter(Show.artist_id == artist_id, Show.start_time <= datetime.now()).all()
    upcoming_shows = Show.query.join(Venue, Venue.id == Show.venue_id) \
        .add_columns(Venue.id.label('venue_id'),
                     Venue.name.label('venue_name'),
                     Venue.image_link.label('venue_image_link'),
                     Show.start_time.label('start_time')) \
        .filter(Show.artist_id == artist_id, Show.start_time > datetime.now()).all()
    if data is not None:
        data.past_shows = past_shows
        data.past_shows_count = len(past_shows)
        data.upcoming_shows = upcoming_shows
        data.upcoming_shows_count = len(upcoming_shows)
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    error = False
    artist = Artist.query.get(artist_id)
    try:
        artist.name = request.form['name']
        artist.city = request.form['city']
        artist.state = request.form['state']
        artist.phone = request.form['phone']
        artist.genres = ','.join(request.form.getlist('genres'))
        artist.facebook_link = request.form['facebook_link']
        artist.image_link = request.form['image_link']
        artist.website = request.form['website_link']
        artist.seeking_venue = \
            (request.form.get('seeking_venue') is not None) & ('y' == request.form.get('seeking_venue'))
        artist.seeking_description = request.form['seeking_description']

        db.session.commit()
    except():
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + artist.name + ' could not be edited.')
    else:
        return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    error = False
    venue = Venue.query.get(venue_id)
    try:
        venue.name = request.form['name']
        venue.city = request.form['city']
        venue.state = request.form['state']
        venue.address = request.form['address']
        venue.phone = request.form['phone']
        venue.genres = ','.join(request.form.getlist('genres'))
        venue.facebook_link = request.form['facebook_link']
        venue.image_link = request.form['image_link']
        venue.website = request.form['website_link']
        venue.seeking_talent = \
            (request.form.get('seeking_talent') is not None) & ('y' == request.form.get('seeking_talent'))
        venue.seeking_description = request.form['seeking_description']

        db.session.commit()
    except():
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Venue ' + venue.name + ' could not be edited.')
    else:
        return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    error = False
    try:
        name = request.form['name']
        city = request.form['city']
        state = request.form['state']
        phone = request.form['phone']
        genres = ','.join(request.form.getlist('genres'))
        facebook_link = request.form['facebook_link']
        image_link = request.form['image_link']
        website = request.form['website_link']
        seeking_venue = (request.form.get('seeking_venue') is not None) & ('y' == request.form.get('seeking_venue'))
        seeking_description = request.form['seeking_description']
        artist = Artist(name=name, city=city, state=state, phone=phone, genres=genres,
                        facebook_link=facebook_link, image_link=image_link, website=website,
                        seeking_venue=seeking_venue, seeking_description=seeking_description)
        db.session.add(artist)
        db.session.commit()
    except():
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Artist ' + artist.name + ' could not be listed.')
    else:
        flash('Artist ' + request.form['name'] + ' was successfully listed!')
        return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------


@app.route('/shows')
def shows():
    data = Show.query.join(Artist, Artist.id == Show.artist_id).join(Venue, Venue.id == Show.venue_id) \
        .add_columns(Venue.id.label('venue_id'),
                     Venue.name.label('venue_name'),
                     Artist.id.label('artist_id'),
                     Artist.name.label('artist_name'),
                     Artist.image_link.label('artist_image_link'),
                     Show.start_time.label('start_time')).all()
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    error = False
    try:
        artist_id = request.form['artist_id']
        venue_id = request.form['venue_id']
        start_time = request.form['start_time']
        artist = Artist.query.get(artist_id)
        venue = Venue.query.get(venue_id)

        show = Show(artist_id=artist.id, venue_id=venue.id, start_time=start_time)
        db.session.add(show)
        db.session.commit()
    except():
        db.session.rollback()
        error = True
    finally:
        db.session.close()
    if error:
        flash('An error occurred. Show could not be listed.')
    else:
        flash('Show was successfully listed!')
        return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
