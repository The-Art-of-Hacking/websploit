#!/usr/bin/env python3
import graphene
from flask import Flask
from flask_graphql import GraphQLView

# --- Mock Database ---
users_db = [
    {
        "id": "1", 
        "username": "admin", 
        "email": "admin@galactic.gov", 
        "api_token": "FLAG{GRAPHQL_INTROSPECTION_MASTER}", 
        "is_admin": True,
        "notes": "System Administrator with full access."
    },
    {
        "id": "2", 
        "username": "skywalker", 
        "email": "luke@rebel.alliance", 
        "api_token": "force-user-001", 
        "is_admin": False,
        "notes": "Pilot. Keep an eye on him."
    },
    {
        "id": "3", 
        "username": "vader", 
        "email": "darth@empire.gov", 
        "api_token": "dark-side-999", 
        "is_admin": False,
        "notes": "Lord Vader."
    }
]

# --- GraphQL Schema ---

class User(graphene.ObjectType):
    id = graphene.ID()
    username = graphene.String()
    email = graphene.String()
    api_token = graphene.String(description="The API Token for the user. Restricted access.")
    is_admin = graphene.Boolean()
    notes = graphene.String()

class SystemInfo(graphene.ObjectType):
    version = graphene.String()
    status = graphene.String()
    debug_mode = graphene.Boolean()

class Query(graphene.ObjectType):
    user = graphene.Field(User, id=graphene.ID(required=True), description="Get a user by ID")
    users = graphene.List(User, description="List all users")
    system_status = graphene.Field(SystemInfo, description="Check the system status")
    
    def resolve_user(self, info, id):
        # Insecure Direct Object Reference (IDOR) equivalent in GraphQL
        # No auth check here!
        for user in users_db:
            if user["id"] == id:
                return User(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    api_token=user["api_token"],
                    is_admin=user["is_admin"],
                    notes=user["notes"]
                )
        return None

    def resolve_users(self, info):
        # Returns all users but filters sensitive info in this view (mocking a "public" list)
        # But if they query 'user(id: "1")' directly, they get everything!
        safe_users = []
        for user in users_db:
            safe_users.append(User(
                id=user["id"],
                username=user["username"],
                email=user["email"],
                api_token="[REDACTED]", # Redacted in the list view
                is_admin=user["is_admin"],
                notes=user["notes"]
            ))
        return safe_users

    def resolve_system_status(self, info):
        return SystemInfo(version="2.0.1-alpha", status="Operational", debug_mode=True)

class CreateUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)
        email = graphene.String(required=True)

    user = graphene.Field(lambda: User)

    def mutate(self, info, username, email):
        user = User(username=username, email=email, id=str(len(users_db) + 1))
        return CreateUser(user=user)

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

# --- Flask App ---
app = Flask(__name__)
app.debug = True

# Add the GraphQL endpoint
app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True  # Enable the GraphiQL interface
    )
)

@app.route('/')
def index():
    return """
    <html>
        <head>
            <title>Galactic Communications Hub</title>
            <style>
                body { font-family: sans-serif; background: #0f172a; color: white; text-align: center; padding: 50px; }
                h1 { color: #3b82f6; }
                a { color: #60a5fa; text-decoration: none; font-size: 1.2em; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>Galactic Communications Hub</h1>
            <p>Welcome to the secure internal API.</p>
            <p>Access the GraphiQL Interface below:</p>
            <br>
            <a href="/graphql">>> Enter GraphiQL Console <<</a>
        </body>
    </html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5023)

