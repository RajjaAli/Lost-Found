from flask import Flask, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

from passlib.apps import custom_app_context as pwd_context
from flask_httpauth import HTTPBasicAuth

import os

#initliazing our flask app, SQLAlchemy and Marshmallow
app = Flask(__name__)
app.secret_key = "super secret key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/lostnfound_db'

#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
ma = Marshmallow(app)


class User(db.Model):
    """User account model."""

    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=False, nullable=False)
    email = db.Column(db.String(40), unique=True, nullable=False)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), primary_key=False, unique=False, nullable=False)

    def __init__(self, name, email, username, password_hash):
        self.name = name
        self.email = email
        self.username = username
        self.password_hash = password_hash

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)


class Country(db.Model):
    __tablename__ = "country"

    id = db.Column(db.Integer, primary_key=True)
    country_name = db.Column(db.String(50))
    country_code = db.Column(db.String(50))

    def __init__(self, country_name, country_code):
        self.country_name = country_name
        self.country_code = country_code


class City(db.Model):
    __tablename__ = "city"

    id = db.Column(db.Integer, primary_key=True)
    city_name = db.Column(db.String(50))
    city_code = db.Column(db.String(50))
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'), nullable=False)
    countryname = db.relationship('Country', backref=db.backref('city', lazy='dynamic'))

    def __init__(self, city_name, city_code, country_id):
        self.city_name = city_name
        self.city_code = city_code
        self.country_id = country_id


class Location(db.Model):
    __tablename__ = "location"

    id = db.Column(db.Integer, primary_key=True)
    address1 = db.Column(db.String(50))
    address2 = db.Column(db.String(50))
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    cityname = db.relationship('City', backref=db.backref('location', lazy='dynamic'))

    def __init__(self, address1, address2, city_id):
        self.address1 = address1
        self.address2 = address2
        self.city_id = city_id


class Item(db.Model):
    __tablename__ = "item"

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(40))
    description = db.Column(db.String(40))
    picture = db.Column(db.String(40))
    created_on = db.Column(db.DateTime, index=True, server_default=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # creationuser = db.relationship('User', backref=db.backref('item', lazy='dynamic'))
    updated_on = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    locationname = db.relationship('Location', backref=db.backref('item', lazy='dynamic'))

    def __init__(self, item_name, description, picture, created_by, location_id):
        self.item_name = item_name
        self.description = description
        self.picture = picture
        self.created_by = created_by
        self.location_id = location_id


db.create_all()


class UserSchema(ma.Schema):
    class Meta:
        fields = ("name", "email", "username", "password_hash")


class CountrySchema(ma.Schema):
    class Meta:
        fields = ("country_name", "country_code")


class CitySchema(ma.Schema):
    class Meta:
        fields = ("city_name", "city_code", "country_id")


class LocationSchema(ma.Schema):
    class Meta:
        fields = ("address1", "address2", "city_id")


class ItemSchema(ma.Schema):
    class Meta:
        fields = ("item_name", "description", "picture", "created_by", "location_id")


user_schema = UserSchema()
users_schema = UserSchema(many=True)

country_schema = CountrySchema()
countries_schema = CountrySchema(many=True)

city_schema = CitySchema()
cities_schema = CitySchema(many=True)

location_schema = LocationSchema()
locations_schema = LocationSchema(many=True)

item_schema = ItemSchema()
items_schema = ItemSchema(many=True)


@app.route('/register', methods=['POST'])
def register_user():
    name = request.json['name']
    email = request.json['email']
    username = request.json['username']
    password = request.json['password']
    if username is None or password is None:
        return ('Argument missing')  # missing arguments
    if User.query.filter_by(username=username).first() is not None:
        return ('Username already exists')  # existing user
    user = User(name,email,username,password)
    user.hash_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({'username': user.username})

@app.route('/login', methods = ['POST'])
def login_user():
    usernamee = request.json['username']
    password_hash = request.json['password']
    current_user = User.query.filter_by(username=usernamee).first()

    userr = User.query.get(current_user.id)

    if (userr.verify_password(password_hash)):
        return ('Hello, %s!' % usernamee)
    else:
        return ('Incorrect username or password')

@app.route('/users', methods = ['GET'])
def get_user():

    all_users = User.query.all()
    result = users_schema.dump(all_users)
    return jsonify(result)


# adding an item
@app.route('/add_item', methods=['POST'])
def add_item():
    item_name = request.json['item_name']
    description = request.json['description']
    picture = request.json['picture']
    created_by = request.json['created_by']
    location_id = request.json['location_id']

    new_item = Item(item_name, description, picture, created_by, location_id)
    db.session.add(new_item)
    db.session.commit()

    return item_schema.jsonify(new_item)


# getting all items
@app.route('/view_items', methods=['GET'])
def get_post():
    all_items = Item.query.all()
    result = items_schema.dump(all_items)

    return jsonify(result)


# searching particular item
@app.route('/search_by_id/<id>', methods=['GET'])
def item_details(id):
    itemm = Item.query.get(id)
    return item_schema.jsonify(itemm)


@app.route('/search_by_location/<lid>', methods=['GET'])
def item_location(lid):
    itemss = Item.query.filter_by(location_id=lid)
    result = items_schema.dump(itemss)
    return jsonify(result)


@app.route('/search_by_name/<i_name>', methods=['GET'])
def item_name(i_name):
    itemss_n = Item.query.filter_by(item_name=i_name)
    result = items_schema.dump(itemss_n)
    return jsonify(result)


# updating post
@app.route('/update_item/<id>', methods=['PUT'])
def item_update(id):
    itemm = Item.query.get(id)

    item_name = request.json['item_name']
    description = request.json['description']
    picture = request.json['picture']
    created_by = request.json['created_by']
    location_id = request.json['location_id']

    itemm.item_name = item_name
    itemm.description = description
    itemm.picture = picture
    itemm.created_by = created_by
    itemm.location_id = location_id

    db.session.commit()
    return item_schema.jsonify(itemm)


# deleting item
@app.route('/delete_item/<id>', methods=['DELETE'])
def item_delete(id):
    item = Item.query.get(id)
    db.session.delete(item)
    db.session.commit()

    return ('Item deleted')


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)