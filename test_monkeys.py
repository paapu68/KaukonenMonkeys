#!flask/bin/python
""" testing with pytest (http://pytest.org)
    using http://alexmic.net/flask-sqlalchemy-pytest/

    database is initialized in app/init_db.py
    Tests assume the following structure of the database:

    admin = Monkey(name='admin', age=12, email='admin@example.com')
    guest = Monkey(name='guest', age=12, email='guest@example.com')
    veeti = Monkey(name='veeti', age=3, email='veeti@example.com')
    kerttu = Monkey(name='kerttu', age=7, email='kerttu@example.com')
    kukka = Monkey(name='kukka', age=10, email='kukka@example.com')

    admin has friend guest, admin's best friend is guest
    guest has friend admin, guest's best friend is admin
    veeti has friends kerttu and and kukka, veeti's best friend is kerttu
    kerttu has friend veeti, kerttu's best friend is veeti
    kukka has friends veeti and kukka, kukka's best friend is veeti
"""
import os
import pytest
import tempfile

from config import basedir

from app.models import Monkey, Friend

test_db_name = 'test.db'
TEST_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, test_db_name)

@pytest.fixture(scope='session')
def myapp(request):
    """Session-wide test `Flask` application."""
    from app import app
    settings_override = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': TEST_DATABASE_URI
    }
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = TEST_DATABASE_URI
    myapp = app

    # Establish an application context before running the tests.
    ctx = myapp.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return myapp


@pytest.fixture(scope='session')
def db(myapp, request):
    """Session-wide test database."""
    from app import db
    from app.init_db import init_db

    def teardown():
        db.drop_all()

    init_db()
    db.app = myapp
    db.create_all()

    request.addfinalizer(teardown)
    return db

@pytest.fixture(scope='function')
def session(db, request):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)

    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    return session

def test_initial_condition(session):
    """ 
    Test that initial test setup is ok.
    That is: it should be as described at the beginning of this file.
    """

    monkeys = Monkey.query.order_by(Monkey.name)
    monkeynames = []
    monkey_lenfriends = []
    for monkey in monkeys:
        monkeynames.append(monkey.name.encode('utf8'))
        monkey_lenfriends.append(monkey.lenfriends)

    assert monkeynames[0] == 'admin'
    assert monkeynames[1] == 'guest'
    assert monkeynames[2] == 'kerttu'
    assert monkeynames[3] == 'kukka'
    assert monkeynames[4] == 'veeti'

    assert monkey_lenfriends[0] == 1
    assert monkey_lenfriends[1] == 1
    assert monkey_lenfriends[2] == 1
    assert monkey_lenfriends[3] == 2
    assert monkey_lenfriends[4] == 2

    friends = Friend.query.order_by(Friend.name)
    monkeynames = []
    friendnames = []
    for friend in friends:
        friendnames.append(friend.name)
        monkeynames.append(friend.to_monkey.name)

    assert monkeynames[0] == 'guest'
    assert monkeynames[1] == 'admin'
    assert monkeynames[2] == 'veeti'
    assert monkeynames[3] in ['kukka', 'veeti'] 
    assert monkeynames[4] in ['kukka', 'veeti'] 
    assert monkeynames[5] in ['kukka', 'kerttu'] 
    assert monkeynames[6] in ['kukka', 'kerttu'] 

    assert friendnames[0] == 'admin'
    assert friendnames[1] == 'guest'
    assert friendnames[2] == 'kerttu'
    assert friendnames[3] == 'kukka'
    assert friendnames[4] == 'kukka'
    assert friendnames[5] == 'veeti'
    assert friendnames[6] == 'veeti'


def test_add(session):
    """ 
    Test that the number of users has increased by one and the 
    last user has the email address 'Jack@gmail.com',
    after we have added one user 
    """
    from testviews import add
    len_before = len(Monkey.query.all())
    add(name='Jack', age=4, email='Jack@gmail.com')
    len_after = len(Monkey.query.all())
    email = Monkey.query.get(len_after).email

    assert email == 'Jack@gmail.com'
    assert (len_after - len_before) == 1

def test_edit(session):
    """ 
    Test editing a monkey 'veeti's' age from 3 to 4.
    """
    from testviews import edit
    monkey = Monkey.query.get(3)
    assert monkey.age == 3
    edit(3, 'veeti', 4, 'veeti@veeti.com')
    monkey.age = 4
    session.commit()

    monkey = Monkey.query.get(3)
    assert monkey.name == 'veeti'
    assert monkey.age == 4
    assert monkey.email == 'veeti@veeti.com'

def test_delete(session):
    """ 
    Test deleting a monkey with a name 'veeti'.

    Number of monkeys should decrease by one.
    Deleted monkey should not be found in the database anymore.

    Number of friends of kerttu should decrease from 1 to 0
    Number of friends of kukka should decrease from 2 to 1

    Best friend of kukka and kerttu should change from 'Veeti' to 'None'

    """
    from testviews import delete
    len_before = len(Monkey.query.all())
    monkey_before = Monkey.query.filter_by(name='veeti').first().name
    #Best friend of kerttu and kukka should be veeti
    monkey = Monkey.query.filter_by(name='kerttu').first()
    assert monkey.best_friend_name == 'veeti'
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.best_friend_name == 'veeti'
    delete(['veeti'])
    len_after = len(Monkey.query.all())
    monkey_after = Monkey.query.filter_by(name='veeti').first()

    #monkey veeti should have been deleted
    assert monkey_before == 'veeti'
    assert monkey_after == None
    #number of monkeys should have decreased by one
    assert (len_after - len_before) == -1
    #Number of friends of kerttu should decrease from 1 to 0
    monkey = Monkey.query.filter_by(name='kerttu').first()
    assert monkey.lenfriends == 0
    #Number of friends of kukka should decrease from 2 to 1
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.lenfriends == 1

    #Best friend of kerttu and kukka should be None because 
    #veeti has been deleted
    monkey = Monkey.query.filter_by(name='kerttu').first()
    assert monkey.best_friend_name == None
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.best_friend_name == None         

def test_friend2(session):
    """ 
    Select new friends for monkey veeti.
    New friends are admin and guest.
    """
    from testviews import friend2

    #initial number of friends of kerttu should be 1
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.lenfriends == 2
    #initial number of friends of kukka should be 2
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.lenfriends == 2
    #number of friends of veeti should remain two
    monkey = Monkey.query.filter_by(name='veeti').first()
    assert monkey.lenfriends == 2
    friend2(3, ['admin', 'guest'])
    monkey = Monkey.query.filter_by(name='veeti').first()
    assert monkey.lenfriends == 2
    #best friend of veeti should be None with new friends
    assert monkey.best_friend_name == None
    #best friend of kukka should be None with new friends
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.best_friend_name == None
    #best friend of kerttu should be None with new friends
    monkey = Monkey.query.filter_by(name='kerttu').first()
    assert monkey.best_friend_name == None
    #final number of friends of kerttu should be zero
    monkey = Monkey.query.filter_by(name='kerttu').first()
    assert monkey.lenfriends == 0    
    #final number of friends of kukka should be one
    monkey = Monkey.query.filter_by(name='kukka').first()
    assert monkey.lenfriends == 1


def test_best_friend2(session):
    """ 
    Change veeti's best friend from kerttu to admin.
    """
    from testviews import best_friend2

    #initial best friend of veeti should be kerttu
    monkey = Monkey.query.filter_by(name='veeti').first()
    assert monkey.best_friend_name == 'kerttu'
    #initial number of friends of admin should be one
    monkey = Monkey.query.filter_by(name='admin').first()
    assert monkey.lenfriends == 1
    #initial number of friends of veeti should be two
    monkey = Monkey.query.filter_by(name='veeti').first()
    assert monkey.lenfriends == 2
    best_friend2(3, 'admin')
    #final best friend of veeti should be admin
    monkey = Monkey.query.filter_by(name='veeti').first()
    assert monkey.best_friend_name == 'admin'
    #final number of friends of admin should be two
    monkey = Monkey.query.filter_by(name='admin').first()
    assert monkey.lenfriends == 2
    #final number of friends of veeti should be three
    monkey = Monkey.query.filter_by(name='veeti').first()
    assert monkey.lenfriends == 3
