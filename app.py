from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
import os
import random
import datetime
from moviepy.editor import vfx
import uuid
import random
import secrets
from PIL import Image
from pathlib import Path
import numpy as np
from moviepy.editor import *

app = Flask(__name__)

app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MUSIC_DIRECTORY'] = 'music'
app.config['OUTPUT_FOLDER'] = 'output'  # Output folder for processed videos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    videos = db.relationship('Video', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    processed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4'}

MUSIC_DIRECTORY = 'music'

def get_random_background_music():
    music_files = os.listdir(MUSIC_DIRECTORY)
    selected_music_file = random.choice(music_files)
    return os.path.join(MUSIC_DIRECTORY, selected_music_file)


def apply_random_adjustments(video_clip, output_path, user_inputs):
    if user_inputs is None:
        user_inputs = {}

    # Additional features
    artist_name = 'Auto Artist'
    current_year = datetime.datetime.now().year
    author_name = 'Auto Author'

    # Check if random adjustments should be applied
    if user_inputs.get('random_adjustments'):
        # Random parameters
        audio_volume = float(user_inputs['audio_volume']) if user_inputs['audio_volume'] is not None else random.uniform(0.9, 1.1)
        brightness_factor = float(user_inputs['brightness_factor']) if user_inputs['brightness_factor'] is not None else random.uniform(0.8, 1.2)
        scale_factor = float(user_inputs['scale_factor']) if user_inputs['scale_factor'] is not None else random.uniform(0.8, 1.2)
        contrast_factor = float(user_inputs['contrast_factor']) if user_inputs['contrast_factor'] is not None else random.uniform(0.8, 1.2)

    else:
        # Use default values if not provided by the user
        audio_volume = random.uniform(0.9, 1.1)
        brightness_factor = random.uniform(0.8, 1.2)
        scale_factor = random.uniform(0.8, 1.2)
        contrast_factor = random.uniform(0.8, 1.2)

    # Apply adjustments to the video clip
    processed_clip = video_clip.volumex(audio_volume)
    processed_clip = processed_clip.fx(vfx.colorx, brightness_factor)
    processed_clip = processed_clip.fx(vfx.resize, scale_factor)

    # Add background music without repetition
    music_directory = 'music'
    used_music_numbers = set()
    while True:
        music_number = random.randint(1, 100)
        if music_number not in used_music_numbers:
            used_music_numbers.add(music_number)
            break

    music_filename = f'{music_number}.mp3'
    music_path = os.path.join(music_directory, music_filename)

    # Load the separated vocals from the video
    separated_vocals_path = "temporary/output/original_audio/vocals.wav"
    separated_vocals = AudioFileClip(separated_vocals_path)

    # Load the new background music
    background_music = AudioFileClip(music_path)

    # Adjust the volume of the background music
    background_music = background_music.volumex(audio_volume)

    # Ensure all clips have the same duration
    target_duration = min(video_clip.duration, separated_vocals.duration, background_music.duration)

    processed_clip = processed_clip.subclip(0, target_duration)
    separated_vocals = separated_vocals.subclip(0, target_duration)
    background_music = background_music.subclip(0, target_duration)

    # Overlay the background music on the separated vocals
    modified_audio = CompositeAudioClip([separated_vocals, background_music])

    # Replace the audio in the video with the modified audio
    processed_clip = processed_clip.set_audio(modified_audio)

    # Change format of the video
    output_filename = f"processed_{uuid.uuid4()}.mp4"

    # Write the processed clip to a file with metadata
    metadata = {
        'audio_volume': audio_volume,
        'brightness_factor': brightness_factor,
        'scale_factor': scale_factor,
        'contrast_factor': contrast_factor,
        'artist_name': artist_name,
        'year': current_year,
        'media': 'Digital',
        'author': author_name,
        # Add more custom metadata fields as needed
    }

    processed_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", ffmpeg_params=["-metadata", f"artist={artist_name}", "-metadata", f"year={current_year}", "-metadata", f"media=Digital", "-metadata", f"author={author_name}"])

    return processed_clip




    




# ... (previous code)

def process_and_save_video(video_path, audio_path=None, output_folder='output', num_copies=100, user_inputs=None):
    try:
        video_clip = VideoFileClip(video_path)

        if audio_path:
            audio_clip = AudioFileClip(audio_path)
            video_clip = video_clip.set_audio(audio_clip)

        for copy_num in range(1, num_copies + 1):
            unique_id = str(uuid.uuid4())
            output_subfolder = os.path.join(output_folder, f'output_{copy_num}')
            os.makedirs(output_subfolder, exist_ok=True)

            output_filename = f"processed_{copy_num}.mp4"
            output_path = os.path.join(output_subfolder, output_filename)

            # Apply random adjustments to each copy
            processed_clip = apply_random_adjustments(video_clip, output_path, user_inputs)

            # Write the processed clip to the output video file
            processed_clip.write_videofile(output_path, codec='libx264', audio_codec='aac')

            # Close the clip to release resources
            processed_clip.close()

            # Mark the video as processed in the database
            new_video = Video(user=current_user, filename=output_filename, processed=True)
            db.session.add(new_video)
            db.session.commit()

    except Exception as e:
        app.logger.error(f"Error processing video: {e}")
        raise


import os
from moviepy.editor import VideoFileClip, AudioFileClip
from spleeter.separator import Separator

def add_vocals_to_video(video_clip, original_audio_path, vocals_volume_factor=1.5):
    try:
        # Use spleeter to separate vocals from the original audio
        separator = Separator('spleeter:2stems')  # Adjust the model based on your preference

        # Ensure the output directory exists
        output_directory = "temporary/output/"
        os.makedirs(output_directory, exist_ok=True)

        separator.separate_to_file(original_audio_path, output_directory)

        # Load the separated vocals from the file
        separated_vocals_path = os.path.join(output_directory, "original_audio/vocals.wav")

        if not os.path.exists(separated_vocals_path):
            raise FileNotFoundError(f"The separated vocals file {separated_vocals_path} could not be found.")

        separated_vocals = AudioFileClip(separated_vocals_path)

        # Adjust the volume of the separated vocals
        
        separated_vocals = separated_vocals.volumex(vocals_volume_factor)

        # Ensure both clips have the same duration
        video_duration = video_clip.duration
        vocals_duration = separated_vocals.duration

        if video_duration != vocals_duration:
            if video_duration < vocals_duration:
                separated_vocals = separated_vocals.subclip(0, video_duration)
            else:
                separated_vocals = separated_vocals.subclip(0, video_duration)

        # Replace the audio in the video with the separated vocals
                
        modified_clip = video_clip.set_audio(separated_vocals)

        return modified_clip

    except Exception as e:
        # Handle exceptions, log the error, and return the original video clip
        print(f"Error adding vocals to video: {e}")
        return video_clip








with app.app_context():
    db.create_all()

@app.route('/')
def index():
    processed_videos = []

    if current_user.is_authenticated:
        processed_videos = Video.query.filter(Video.user.has(id=current_user.id), Video.processed.is_(True)).all()

    return render_template('index.html', processed_videos=processed_videos)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()

        if existing_user:
            flash('Username or email already exists. Please choose a different one.', 'danger')
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4'}


@app.route('/upload', methods=['POST'])
@login_required
def upload():
    # Check if the checkbox is checked
    random_adjustments = 'random_adjustments' in request.form

    # Additional user inputs
    user_inputs = {
        'random_adjustments': random_adjustments,
        'speed_factor': request.form.get('speed_factor', None),
        'audio_volume': request.form.get('audio_volume', None),
        'brightness_factor': request.form.get('brightness_factor', None),
        'scale_factor': request.form.get('scale_factor', None),
        'contrast_factor': request.form.get('contrast_factor', None),
    }

    if 'video' not in request.files:
        flash('No video file part', 'danger')
        return redirect(url_for('index'))

    video = request.files['video']

    if video.filename == '':
        flash('No selected video file', 'danger')
        return redirect(url_for('index'))

    if video and allowed_file(video.filename):
        video_filename = secure_filename(video.filename)

        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)

        video.save(video_path)

        # Get the path to the original audio of the video
        original_audio_path = "temporary/original_audio.wav"
        VideoFileClip(video_path).audio.write_audiofile(original_audio_path)

        # Use the updated function to add vocals to the modified video
        modified_clip = add_vocals_to_video(VideoFileClip(video_path), original_audio_path)

        # Save the modified video to a new file
        modified_video_path = os.path.join(app.config['UPLOAD_FOLDER'], 'modified_' + video_filename)
        modified_clip.write_videofile(modified_video_path, codec='libx264', audio_codec='aac')
        modified_clip.close()

        # Further processing and saving of the video
        process_and_save_video(modified_video_path, num_copies=100, user_inputs=user_inputs)

        new_video = Video(user=current_user, filename=video_filename, processed=True)
        db.session.add(new_video)
        db.session.commit()

        flash('Video processed successfully', 'success')
        return redirect(url_for('index'))

    flash('Invalid video file format. Please upload a valid MP4 video.', 'danger')
    return redirect(url_for('index'))


# Ensure the necessary folders exist

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/download/<filename>')
@login_required
def download(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)
