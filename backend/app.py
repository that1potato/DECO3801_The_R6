import io
import os
from PIL import Image
from datetime import datetime

from flask import Flask, request, jsonify, after_this_request
from flask_cors import CORS, cross_origin

from search_engine_access import generate_image_caption, search_pinterest, response_pull_images
from transformers import BlipProcessor, BlipForConditionalGeneration

from controlnet.sd_backbone import StableDiffusionBackBone

# Database
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.mysql import LONGTEXT


app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://ryuto:ryuto@localhost/ArtAssistant'
# Folder to temporarily save generation results
GENERATION_FOLDER = './generations'
app.config['GENERATION_FOLDER'] = GENERATION_FOLDER
os.makedirs(GENERATION_FOLDER, exist_ok=True)

# Initialising blip
blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir='blip_weights')
blip = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base", cache_dir='blip_weights')

# Initialising sdbackbone
webui_url = 'http://127.0.0.1:7860'
bb = StableDiffusionBackBone(webui_url)

# Creating Database
db = SQLAlchemy(app)

# temporarily user_name is replaced with user_email
class Users(db.Model):
    __tablename__ = 'Users'
    user_id = db.Column(db.Integer, primary_key = True)
    user_email = db.Column(db.String(255), unique = True)
    user_password = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default = datetime.now)

    # def __init__(self, user_email, user_password):
    #     self.user_email = user_email
    #     self.user_password = user_password

@app.route('/users/get', methods = ['GET'])
def get_users():
    print(request.method)
    if request.method == 'GET':
        users = Users.query.all()
        users_list = [
        {
            "user_id": user.user_id,
            "user_email": user.user_email,
            "user_password": user.password,
            "created_at": user.created_at.isoformat()  # Convert datetime to string
        }
        for user in users
        ]
        return jsonify(users_list)

@app.route('/users/insert', methods=['POST'])
# @cross_origin
def insert_user():
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_user = Users(user_email = data['user_email'],
                            user_password = data['user_password'])
            db.session.add(new_user)
            db.session.commit()
            return jsonify({'user_id': new_user.user_id,
                            'user_email': new_user.user_email,
                            'user_password': new_user.user_password,
                            'created_at': new_user.created_at}), 201
        except Exception as e:
            db.session.rollback()
            return {}, 500
    return {}, 405

class SearchImage(db.Model):
    __tablename__ = 'SearchImage'
    s_image_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'))
    s_image_file_path = db.Column(LONGTEXT)
    created_at = db.Column(db.DateTime, default = datetime.now)

@app.route('/search_image/get', methods = ['GET'])
def get_search_imgs():
    print(request.method)
    if request.method == 'GET':
        search_imgs = SearchImage.query.all()
        search_imgs_list = [
        {
            "s_image_id": search_img.s_image_id,
            "user_id": search_img.user_id,
            "s_image_file_path": search_img.s_image_file_path,
            "created_at": search_img.created_at.isoformat()  # Convert datetime to string
        }
        for search_img in search_imgs
        ]
        return jsonify(search_imgs_list)
    
@app.route('/search_image/insert', methods=['POST'])
# @cross_origin
def insert_search_image():
    '''
    Inserts the new search image to the database

    IMPORTANT:
        The endpoint assumes that it will be handed with a user_id. IT DOES NOT FETCH 
    '''
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_search_image = SearchImage(user_id = data['user_id'],
                                   s_image_file_path = data['s_image_file_path'])
            db.session.add(new_search_image)
            db.session.commit()
            return jsonify({'s_image_id': new_search_image.s_image_id,
                            'user_id': new_search_image.user_id,
                            's_image_file_path': new_search_image.s_image_file_path,
                            'created_at': new_search_image.created_at}), 201
        except Exception as e:
            db.session.rollback()
            return {}, 500
    return {}, 405

class SearchText(db.Model):
    __tablename__ = 'SearchText'
    s_text_id = db.Column(db.Integer, primary_key = True)
    s_image_id = db.Column(db.Integer, db.ForeignKey('SearchImage.s_image_id'))
    s_text_query = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default = datetime.now)

@app.route('/search_text/get', methods = ['GET'])
def get_search_text():
    print(request.method)
    if request.method == 'GET':
        search_texts = SearchImage.query.all()
        search_texts_list = [
        {
            "s_text_id": search_text.s_text_id,
            "s_image_id": search_text.s_image_id,
            "s_text_query": search_text.s_text_query,
            "created_at": search_text.created_at.isoformat()  # Convert datetime to string
        }
        for search_text in search_texts
        ]
        return jsonify(search_texts_list)
    
@app.route('/search_text/insert', methods=['POST'])
# @cross_origin
def insert_search_text():
    '''
    Inserts the new search image to the database

    IMPORTANT:
        The endpoint assumes that it will be handed with a user_id. IT DOES NOT FETCH 
    '''
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_search_text = SearchText(user_id = data['user_id'],
                                   s_text_query = data['s_image_file_path'])
            db.session.add(new_search_text)
            db.session.commit()
            return jsonify({'s_text_id': new_search_text.s_text_id,
                            's_image_id': new_search_text.s_image_id,
                            's_text_query': new_search_text.s_text_query,
                            'created_at': new_search_text.created_at.isoformat()}), 201
        except Exception as e:
            db.session.rollback()
            return {}, 500
    return {}, 405

class GenerateImage(db.Model):
    __tablename__ = 'GenerateImage'
    g_image_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'))
    g_image_file_path = db.Column(LONGTEXT)
    created_at = db.Column(db.DateTime, default = datetime.now)

@app.route('/generate_image/get', methods = ['GET'])
def get_generate_imgs():
    print(request.method)
    if request.method == 'GET':
        generate_imgs = SearchImage.query.all()
        generate_imgs_list = [
        {
            "g_image_id": generate_img.g_image_id,
            "user_id": generate_img.user_id,
            "g_image_file_path": generate_img.g_image_file_path,
            "created_at": generate_img.created_at.isoformat()  # Convert datetime to string
        }
        for generate_img in generate_imgs
        ]
        return jsonify(generate_imgs_list)
    
@app.route('/generate_image/insert', methods=['POST'])
# @cross_origin
def insert_generate_image():
    '''
    Inserts the new generate image to the database

    IMPORTANT:
        The endpoint assumes that it will be handed with a user_id. IT DOES NOT FETCH 
    '''
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_generate_image = GenerateImage(user_id = data['user_id'],
                                   g_image_file_path = data['s_image_file_path'])
            db.session.add(new_generate_image)
            db.session.commit()
            return jsonify({'g_image_id': new_generate_image.g_image_id,
                            'user_id': new_generate_image.user_id,
                            'g_image_file_path': new_generate_image.g_image_file_path,
                            'created_at': new_generate_image.created_at.isoformat()}), 201
        except Exception as e:
            db.session.rollback()
            return {}, 500
    return {}, 405

class GenerateText(db.Model):
    __tablename__ = 'GenerateText'
    g_text_id = db.Column(db.Integer, primary_key = True)
    g_image_id = db.Column(db.Integer, db.ForeignKey('GenerateImage.g_image_id'))
    g_text_query = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default = datetime.now)

@app.route('/generate_text/get', methods = ['GET'])
def get_generate_text():
    print(request.method)
    if request.method == 'GET':
        generate_texts = SearchImage.query.all()
        generate_texts_list = [
        {
            "g_text_id": generate_text.g_text_id,
            "g_image_id": generate_text.g_image_id,
            "g_text_query": generate_text.g_text_query,
            "created_at": generate_text.created_at.isoformat()  # Convert datetime to string
        }
        for generate_text in generate_texts
        ]
        return jsonify(generate_texts_list)
    
@app.route('/generate_text/insert', methods=['POST'])
# @cross_origin
def insert_generate_text():
    '''
    Inserts the new search image to the database

    IMPORTANT:
        The endpoint assumes that it will be handed with a user_id. IT DOES NOT FETCH 
    '''
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_generate_text = GenerateText(g_image_id = data['g_image_id'],
                                   g_text_query = data['g_text_query'])
            db.session.add(new_generate_text)
            db.session.commit()
            return jsonify({'g_text_id': new_generate_text.g_text_id,
                            'g_image_id': new_generate_text.g_image_id,
                            'g_text_query': new_generate_text.g_text_query,
                            'created_at': new_generate_text.created_at}), 201
        except Exception as e:
            db.session.rollback()
            return {}, 500
    return {}, 405

class SavedImage(db.Model):
    __tablename__ = 'SavedImage'
    sd_image_id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id'))
    sd_image_path = db.Column(LONGTEXT)
    created_at = db.Column(db.DateTime, default = datetime.now)

@app.route('/saved_image/get', methods = ['GET'])
def get_saved_imgs():
    print(request.method)
    if request.method == 'GET':
        saved_imgs = SearchImage.query.all()
        saved_imgs_list = [
        {
            "sd_image_id": saved_img.sd_image_id,
            "user_id": saved_img.user_id,
            "sd_image_file_path": saved_img.sd_image_path,
            "created_at": saved_img.created_at.isoformat()  # Convert datetime to string
        }
        for saved_img in saved_imgs
        ]
        return jsonify(saved_imgs_list)
    
@app.route('/saved_image/insert', methods=['POST'])
# @cross_origin
def insert_saved_image():
    '''
    Inserts the new saved image to the database

    IMPORTANT:
        The endpoint assumes that it will be handed with a user_id. IT DOES NOT FETCH 
    '''
    if request.method == 'POST':
        try:
            data = request.get_json()
            new_saved_image = SavedImage(user_id = data['user_id'],
                                   sd_image_path = data['s_image_file_path'])
            db.session.add(new_saved_image)
            db.session.commit()
            return jsonify({'sd_image_id': new_saved_image.sd_image_id,
                            'user_id': new_saved_image.user_id,
                            'sd_image_path': new_saved_image.sd_image_path,
                            'created_at': new_saved_image.created_at.isoformat()}), 201
        except Exception as e:
            db.session.rollback()
            return {}, 500
    return {}, 405

@app.route('/search', methods = ['POST'])
@cross_origin()
def search():
    '''
    Retrive data from the Pinterest API using the keyword or an image submitted by the user.

    This endpoint returns a list of images as a JSON boject.

    Returns:
        Response: A JSON response with a unique id for each image.
    '''
    if request.method == 'POST':
        if 'query' in request.get_json():
            keyword = request.get_json().get('query')
            raw_imgs = search_pinterest(keyword)
        else:
            source_img = request.get_json('image')
            caption = generate_image_caption(image_path=source_img, model=blip, processor=blip_processor)
            raw_imgs = search_pinterest(caption)

        images = response_pull_images(raw_imgs)
        response = dict()
        for i in range(len(images)):
            response[i] = images[i]
        return jsonify(response), 200
    else:
        return {}, 405

@app.route('/upload', methods = ['POST'])
@cross_origin()
def upload():
    if request.method != 'POST':
        return {}, 405
    
    bb.reset()

    # Handle image files and associated options
    idx = 0
    while True:
        image_key = f'image{idx}'
        option_key = f'option{idx}'

        image_file = request.files.get(image_key)
        option_value = request.form.get(option_key)

        if image_file and option_value:
            bb.add_control_unit(
                unit_num=idx,
                image_path=image_file,
                module=option_value,
                # TODO: missing intensity
            )
        else:
            break

        idx += 1

    prompt = request.form.get('text')
    inpaint_image = request.files.get('canvasImage')
    # TODO: missing inpaint mask
    inpaint_mask = None
    # TODO: missing keep aspect ratio flag
    
    if inpaint_image and inpaint_mask:
        bb.add_inpaint_image(inpaint_image)
        bb.add_inpaint_mask(inpaint_mask)
        output = bb.img2img_inpaint(
            prompt=prompt,
            # TODO: missing keep aspect ratio flag
        )
    else:
        output = bb.txt2img(prompt=prompt)
    
    response = {}
    for idx, img in enumerate(output):
        file_name = f'{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{prompt}_{idx}.png'
        file_path = os.path.join(app.config['GENERATION_FOLDER'], file_name)
        img.save(file_path, format='PNG')
        
        response[idx] = file_name
    
    @after_this_request
    def delete_generations(r):
        '''delete generated images after they got sent back'''
        for file in response.values():
            file_path = os.path.join(app.config['GENERATION_FOLDER'], file)
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error deleting file {file}: {e}")
        return r
    
    return jsonify(response), 200


if __name__ == '__main__':

    with app.app_context():
        db.create_all()

        app.run(host='localhost', debug=True)