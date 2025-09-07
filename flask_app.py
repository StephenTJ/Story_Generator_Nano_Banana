from flask import Flask, render_template, request, jsonify, session
import os
import traceback
from config import Config
from backend.story_generator import StoryGenerator
from backend.utils import validate_api_credentials


app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

story_generator = StoryGenerator()

@app.route('/')
def index():
    """Main page"""
    api_ready = validate_api_credentials(Config.GEMINI_API_KEY, Config.MODEL_ID)
    return render_template('index.html', 
                            api_ready=api_ready,
                            default_prompt=Config.DEFAULT_PROMPT,
                            default_scenes=Config.DEFAULT_DESIRED_SCENES)

@app.route('/api/generate', methods=['POST'])
def generate_story():
    """API endpoint to generate a story"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        prompt = data.get('prompt', '').strip()
        desired_scenes = int(data.get('desired_scenes', Config.DEFAULT_DESIRED_SCENES))
        quality = data.get('quality', 'standard')
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
            
        if not validate_api_credentials(Config.GEMINI_API_KEY, Config.MODEL_ID):
            return jsonify({'error': 'API credentials not configured'}), 500
            
        # Generate the story (always using server TTS)
        result = story_generator.generate_story(prompt, desired_scenes, quality)
        
        # Return the data directly (don't store in session to avoid cookie size limits)
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        print(f"Error generating story: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500


if __name__ == '__main__':
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=5001)
