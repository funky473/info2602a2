import os, csv
import datetime
from flask import Flask, request, redirect, render_template, url_for, flash # type: ignore
from flask_cors import CORS # type: ignore
from sqlalchemy.exc import IntegrityError # type: ignore
from flask_jwt_extended import ( 
    JWTManager,
    create_access_token,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
    current_user
)
from .models import db, User, UserPokemon, Pokemon

# Configure Flask App
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'MySecretKey'
app.config['JWT_ACCESS_COOKIE_NAME'] = 'access_token'
app.config['JWT_REFRESH_COOKIE_NAME'] = 'refresh_token'
app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=15)
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_SECRET_KEY"] = "super-secret"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config['JWT_HEADER_NAME'] = "Cookie"


# Initialize App 
db.init_app(app)
app.app_context().push()
CORS(app)
jwt = JWTManager(app)

# JWT Config to enable current_user
@jwt.user_identity_loader
def user_identity_lookup(user):
  return user.id

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
  identity = jwt_data["sub"]
  return User.query.get(identity)


# *************************************

# Initializer Function to be used in both init command and /init route
# Parse pokemon.csv and populate database and creates user "bob" with password "bobpass"
def initialize_db():
  db.drop_all()
  db.create_all()
  with open('pokemon.csv', newline='', encoding='utf8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
      if row['height_m'] == '':
        row['height_m'] = None
      if row['weight_kg'] == '':
        row['weight_kg'] = None
      if row['type2'] == '':
        row['type2'] = None

      pokemon = Pokemon(name=row['name'], attack=row['attack'], defense=row['defense'], sp_attack=row['sp_attack'], sp_defense=row['sp_defense'], weight=row['weight_kg'], height=row['height_m'], hp=row['hp'], speed=row['speed'], type1=row['type1'], type2=row['type2'])
      db.session.add(pokemon)
    bob = User(username='bob', email="bob@mail.com", password="bobpass")
    db.session.add(bob)
    funky = User(username='funky473', email="funky@mail.com", password="funkypass")
    db.session.add(funky)
    db.session.commit()
    bob.catch_pokemon(1, "Benny")
    bob.catch_pokemon(25, "Saul")
    bob.catch_pokemon(4, "Bobby")
    funky.catch_pokemon(1, "Funky")

# ********** Routes **************

# Template implementation (don't change)

@app.route('/init')
def init_route():
  initialize_db()
  return redirect(url_for('login_page'))

@app.route("/", methods=['GET'])
def login_page():
  return render_template("login.html")

@app.route("/signup", methods=['GET'])
def signup_page():
    return render_template("signup.html")

@app.route("/signup", methods=['POST'])
def signup_action():
  response = None
  try:
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    user = User(username=username, email=email, password=password)
    db.session.add(user)
    db.session.commit()
    response = redirect(url_for('home_page'))
    token = create_access_token(identity=user)
    set_access_cookies(response, token)
  except IntegrityError:
    flash('Username already exists')
    response = redirect(url_for('signup_page'))
  flash('Account created')
  return response

@app.route("/logout", methods=['GET'])
@jwt_required()
def logout_action():
  response = redirect(url_for('login_page'))
  unset_jwt_cookies(response)
  flash('Logged out')
  return response

# *************************************

# Page Routes (To Update)

@app.route("/app", methods=['GET'])
@app.route("/app/<int:pokemon_id>", methods=['GET'])
@jwt_required()
def home_page(pokemon_id=1):
    pokemons = get_pokemons()
    pokemon = Pokemon.query.filter_by(id=pokemon_id).first()
    userpokemons = UserPokemon.query.filter_by(user_id=current_user.id).all()
    return render_template("home.html", 
                         pokemons=pokemons, 
                         pokemon=pokemon, 
                         pokemon_id=pokemon_id-1, 
                         userpokemons=userpokemons,
                         Pokemon=Pokemon)  # Add this line

# Action Routes (To Update)
def login_user(username, password):
  user = User.query.filter_by(username=username).first()
  if user and user.check_password(password):
    token = create_access_token(identity=user)
    return token
  return None

@app.route("/login", methods=['POST'])
def login_action():
  data = request.form
  token = login_user(data['username'], data['password'])
  print(token)
  response = None
  if token:
    flash('Logged in successfully.')  # send message to next page
    response = redirect(
        url_for('home_page'))  # redirect to main page if login successful
    set_access_cookies(response, token)
  else:
    flash('Invalid username or password')  # send message to next page
    response = redirect(url_for('login_page'))
  return response

@app.route("/pokemon/<int:pokemon_id>", methods=['POST'])
@jwt_required()
def capture_action(pokemon_id):
    pokemon_name = request.form.get("pokemon_name")
    try:
        # Verify pokemon exists first
        pokemon = Pokemon.query.get(pokemon_id)
        if not pokemon:
            flash('Pokemon not found')
            return redirect(url_for('home_page'))
            
        # Check if user already has this pokemon
        existing = UserPokemon.query.filter_by(
            user_id=current_user.id, 
            pokemon_id=pokemon_id
        ).first()
        
        if existing:
            flash('You already have this Pokemon')
            return redirect(url_for('home_page'))
            
        # Create new UserPokemon instance
        new_pokemon = UserPokemon(
            user_id=current_user.id,
            pokemon_id=pokemon_id,
            name=pokemon_name
        )
        
        # Add and commit to database
        db.session.add(new_pokemon)
        db.session.commit()
        
        flash('Pokemon captured successfully')
            
    except Exception as e:
        print(f"Error: {str(e)}")  # Add logging for debugging
        db.session.rollback()
        flash('Error capturing Pokemon')
        
    return redirect(url_for('home_page'))

@app.route("/rename-pokemon/<int:pokemon_id>", methods=['POST'])
@jwt_required()
def rename_action(pokemon_id):
  # implement rename pokemon, show a message then reload page
  rename = request.form.get("rename")
  res = UserPokemon.query.filter_by(user_id=current_user.id, pokemon_id=pokemon_id).first()
  res.name = rename
  db.session.add(res)
  db.session.commit()
  if not res:
    flash('Pokemon not renamed')
  else:
    flash('Pokemon renamed')
  return redirect(url_for('home_page'))

@app.route("/release-pokemon/<int:pokemon_id>", methods=['GET'])
@jwt_required()
def release_action(pokemon_id):
  # implement release pokemon, show a message then reload page
  res = UserPokemon.query.filter_by(pokemon_id=pokemon_id, user_id=current_user.id).first()
  if res:
    db.session.delete(res)
    db.session.commit()
    flash('Pokemon released')
  else:
    flash('Pokemon could not release')
  return redirect(url_for('home_page'))

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8080)

def get_pokemons():
  pokemons = Pokemon.query.all()
  return pokemons
