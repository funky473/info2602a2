import click
from App import app, initialize_db

@app.cli.command("init", help="Creates and initializes the database")
def initialize():
  initialize_db()
  print('database initialized')

@app.cli.command("create-user", help="Creates a new user")
@click.argument("username")
@click.argument("password")
@click.argument("email")
def create_user(username, password, email):
  from App.models import User
  from App import db
  user = User(username=username, password=password, email=email)
  db.session.add(user)
  db.session.commit()
  print(f'User {username} created successfully')