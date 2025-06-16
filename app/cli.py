import click
from flask.cli import with_appcontext
from .extensions import db
from .models import User, Role

@click.command('create-admin')
@with_appcontext
def create_admin() -> None:
    """Create an admin user interactively."""
    email = click.prompt('Email')
    password = click.prompt('Password', hide_input=True)
    role_name = click.prompt('Role')

    role = Role.query.filter_by(name=role_name).first()
    if role is None:
        click.echo(f"Role '{role_name}' not found.")
        return
    if User.query.filter_by(email=email).first():
        click.echo(f"User {email} already exists.")
        return

    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created user {email} with role {role.name}.")

__all__ = ['create_admin']
