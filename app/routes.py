import os
from flask import render_template, url_for, flash, redirect, request, abort, make_response, send_file, jsonify
from app.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, SearchForm
from app.models import User, Post
from app import app, db, bcrypt, cache
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
import csv
from datetime import datetime, timedelta
import jwt
from functools import wraps
from flask_restful import Api, Resource
import requests, json
from app.gen_pdf import create_pdf

@app.route('/')
@cache.cached(timeout=30)
def index():
    return home()

@app.route('/home')
@login_required
def home():
    posts = Post.query.all()
    form = search
    return render_template('home.html', posts=posts, title='Home', )

@app.route('/about')
def about():
    return render_template('about.html', title='About Us')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}, Kindly login to continue.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Sign Up', form=form)
    
def token_required(func):
    @wraps(func)
    def decorated(*args,**kwargs):
        token = None

        if 'token' in request.args:
            token=request.args['token']
        if not token:
            return jsonify({'response':'token missing'})
        try:
            data = jwt.decode(token,app.config['SECRET_KEY'])
            current_user= User.query.filter_by(username=current_user.username).first_or_404()
        except jwt.ExpiredSignatureError:
            return jsonify({'response':'token has expired!','success':False})
        except jwt.InvalidSignatureError:
            return jsonify({'response':'token is Invalid!','success':False})
        except jwt.DecodeError:
            return jsonify({'response':'token is Invalid!','success':False})
        return func(current_user,*args,**kwargs)
    return decorated


@app.route('/unprotected')
def unprotected():
    return jsonify({'message': 'Anyone can view this!'})

@app.route('/protected')
@token_required
def protected():
    return jsonify({'message': 'Users with valid tokens.'})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            token = jwt.encode({'public_id': user.id, 'exp': datetime.utcnow() + timedelta(minutes=30)}, app.config['SECRET_KEY'], algorithm="HS256")
            response = make_response(redirect(next_page) if next_page else redirect(url_for('home')))
            response.set_cookie('token')
            return response

        else:
            flash('Incorrect username or password!', 'danger')

    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

def token_required(f):
   @wraps(f)
   def decorator(*args, **kwargs):
       token = None
       if 'x-access-tokens' in request.headers:
           token = request.headers['x-access-tokens']
 
       if not token:
           return jsonify({'message': 'a valid token is missing'})
       try:
           data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
           current_user = User.query.filter_by(public_id=data['public_id']).first()
       except:
           return jsonify({'message': 'token is invalid'})
 
       return f(current_user, *args, **kwargs)
   return decorator


def save_profile_photo(photo):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(photo.filename)
    photo_fn = random_hex + f_ext
    photo_path = os.path.join(app.root_path, 'static/pp', photo_fn)
    photo.save(photo_path)
    output_size = (150, 150)
    i = Image.open(photo_path)
    i.thumbnail(output_size)
    i.save(photo_path)
    return photo_fn

@app.route('/profile/<string:username>')
@login_required
def profile(username):
    if username == current_user.username:
        return redirect(url_for('account'))
    user = User.query.filter_by(username=username).first_or_404()
    profile_photo = url_for('static', filename='pp/' + user.profile_photo)
    posts = Post.query.filter_by(author=user)
    follower_count = user.follower_count
    blog_count = user.blog_count
    followers = user.followers
    following = user.following
    return render_template('profile.html', user=user, posts=posts, profile_photo=profile_photo, 
                            follower_count=follower_count, blog_count=blog_count, followers=followers,
                            following=following)

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    user = User.query.filter_by(username=current_user.username).first_or_404()
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.pic.data:
            profile_photo = save_profile_photo(form.pic.data)
            current_user.profile_photo = profile_photo
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Updated Successfully', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    profile_photo = url_for('static', filename='pp/' + current_user.profile_photo)
    follower_count = current_user.follower_count
    blog_count = current_user.blog_count
    posts = Post.query.filter_by(author=current_user)
    following = current_user.following
    followers = current_user.followers
    return render_template('account.html', title='Account', posts=posts, profile_photo=profile_photo, 
                                    follower_count = follower_count,form=form, blog_count=blog_count, 
                                    following=following, followers=followers, user=user)

@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        current_user.blog_count += 1
        db.session.commit()
        flash('Blog Posted!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')

@app.route('/post/<int:post_id>')
@cache.cached(timeout=30)
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Blog Updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')

@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    current_user.blog_count -= 1
    db.session.commit()
    flash('Blog Deleted!', 'success')
    return redirect(url_for('home'))



@app.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.pic.data:
            profile_photo = save_profile_photo(form.pic.data)
            current_user.profile_photo = profile_photo
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Updated Successfully', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    profile_photo = url_for('static', filename='pp/' + current_user.profile_photo)
    return render_template('update_profile.html', title='Update Profile', form=form)

@app.route('/follow/<string:username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('home'))
    if current_user.username in user.followers:
        flash('You are already following {}.'.format(username), 'danger')
        return redirect(url_for('profile', username=username))
    else:
        user.followers += current_user.username + ","
        current_user.following += username + ","
        user.follower_count += 1
        db.session.commit()
        flash('You started following {}!'.format(username), 'success')
        return redirect(url_for('profile', username=username))


@app.route('/unfollow/<string:username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if current_user.username not in user.followers:
        flash('You are not following {}.'.format(username))
        return redirect(url_for('profile', username=username))
    else:
        user.followers = user.followers.replace(current_user.username + ",", "")
        current_user.following = current_user.following.replace(username + ",", "")
        user.follower_count -= 1
        db.session.commit()
        flash('You unfollowed {}!'.format(username), 'success')
        return redirect(url_for('profile', username=username))


@app.route('/download/<user_id>')
@login_required
def download_csv(user_id):
    # posts = Post.query.filter_by(user_id=user_id).all()
    user = User.query.filter_by(id=user_id).first()
    # file = os.path.join(app.root_path, 'downloads', 'user_data.csv')
    # os.makedirs(os.path.dirname(file), exist_ok=True)
    # with open(file, 'w', newline='') as f:
    #     writer = csv.writer(f)
    #     writer.writerow(['', '', '', '', '', ''])
    #     writer.writerow(['Title', 'Date posted', 'Content', 'followers', 'following'])
    #     for post in posts:
    #         writer.writerow([post.title, post.date_posted, post.content, user.followers, user.following])

    file = create_pdf(user.username)

    response = make_response(file(file, as_attachment=True))

    return response

@app.route('/stats')
@login_required
def stats():
    three_months_ago = datetime.now() - timedelta(days=90)
    followers = User.query.filter(User.date > three_months_ago).all()
    dates = [follower.date_followed for follower in followers]
    follower_counts = [follower.count for follower in followers]
    return render_template('stats.html', title='Stats', legend='Your Stats', user=current_user) 


# @app.route('/search', methods=['GET', 'POST'])
# @login_required
# def search():
#     form = SearchForm()
#     print(form.errors)
#     if form.validate_on_submit():
#         search = form.search.data
#         users = User.query.filter(User.username.like('%' + search + '%')).all()
#         return render_template('searchreuslt.html', title='Search', form=form, results=users, legend='Search')
#     return render_template('search.html', title='Search', form=form, legend='Search')

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    form = SearchForm()
    print(form.errors)
    if form.validate_on_submit():
        search = form.search.data
        result = api_search(search)
        json_obj = json.loads(result.data.decode('utf-8'))

        usernames=[]
        for item in json_obj:
            username = item['username']
            usernames.append(username)
        # if usernames:
        #     results = response.json().get('results')
        return render_template('searchresult.html', title='Search', form=form, results=usernames, legend='Search')
    return render_template('search.html', title='Search', form=form, legend='Search')

@app.route('/followers/<string:username>')
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first()
    followers = user.followers.split(",")
    return render_template('followers.html', followers=followers, title='Followers')

@app.route('/following/<string:username>')
@login_required
def following(username):
    user = User.query.filter_by(username=username).first()
    following = user.following.split(",")
    return render_template('following.html', followings=following, title='Following')

#--------------------APIs--------------------#

@app.route('/api/search/<string:search>', methods=['GET', 'POST'])
@login_required
def api_search(search):
    # Get all users whose usernames match the search string
    users = User.query.filter(User.username.like('%' + search + '%')).all()
    dic = []
    for user in users:
        dic.append(user.to_dict())
    if len(dic) == 0:
        return jsonify({'error': 'No users found'}), 404
    return jsonify(dic)

@app.route('/api/user/<int:user_id>', methods=['GET'])
@cache.cached(timeout=30)
@login_required
def get_users(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'message': 'No user found!'})
    userdata = {}
    userdata['id'] = user.id
    userdata['username'] = user.username
    userdata['email'] = user.email
    userdata['followers'] = len(user.followers)
    userdata['following'] = len(user.following)
    userdata['profile_photo'] = "http://localhost:5000" + url_for('static', filename='pp/' + user.profile_photo)
    return jsonify(userdata)


@app.route('/api/user/post/<int:user_id>/<int:post_id>', methods=['GET'])
@cache.cached(timeout=30)
@login_required
def get_user_post(user_id, post_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'message': 'No user found!'})
    post = Post.query.filter_by(id=post_id).first()
    if not post:
        return jsonify({'message': 'No post found!'})
    postdata = {}
    postdata['id'] = post.id
    postdata['title'] = post.title
    postdata['date_posted'] = post.date_posted
    postdata['content'] = post.content
    return jsonify(postdata)

@app.route('/api/user/followers/<int:user_id>', methods=['GET'])
@cache.cached(timeout=30)
@login_required
def get_user_followers(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'message': 'No user found!'})
    followers = user.followers.split(",")
    return jsonify(followers)


@app.route('/api/user/following/<int:user_id>', methods=['GET'])
@cache.cached(timeout=30)
def get_user_following(user_id):
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({'message': 'No user found!'})
    following = user.following.split(",")
    return jsonify(following)

@app.route('/api/user/<int:user_id>/new_post/', methods=['GET', 'POST'])
@login_required
@cache.cached(timeout=30)
def api_new_post(user_id):
    if request.method == 'GET':
        return jsonify({'message': 'Use POST method to create a new post.'})
    elif request.method == 'POST':
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return jsonify({'message': 'No user found!'})
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        if not title or not content:
            return jsonify({'message': 'Title and content are required!'})
        post = Post(title=title, content=content, author=user)
        db.session.add(post)
        db.session.commit()
        return jsonify({'message': 'Post created successfully!'})

@app.route('/api/posts/edit/<int:id>', methods=['PUT', 'PATCH'])
@login_required
def api_edit_post(id):
    post = Post.query.get_or_404(id)
    if post.user != current_user:
        abort(403)  # Forbidden

    data = request.json
    post.title = data.get('title', post.title)
    post.content = data.get('content', post.content)
    db.session.commit()

    response = jsonify({'message': 'Post updated', 'post': post.to_dict()})
    response.status_code = 200
    return response

@app.route('/api/posts/delete/<int:id>', methods=['DELETE'])
@login_required
def api_delete_post(id):
    post = Post.query.get_or_404(id)
    if post.user != current_user:
        abort(403)

    db.session.delete(post)
    db.session.commit()

    response = jsonify({'message': 'Post deleted'})
    response.status_code = 200
    return response
