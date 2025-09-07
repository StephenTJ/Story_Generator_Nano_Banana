class StoryApp {
    constructor() {
        this.form = document.getElementById('storyForm');
        this.promptEl = document.getElementById('prompt');
        this.scenesEl = document.getElementById('desired_scenes');
        this.ttsEl = document.getElementById('tts_mode');

        this.loading = document.getElementById('loading');
        this.loadingText = document.getElementById('loadingText');
        this.viewerSection = document.getElementById('viewerSection');
        this.inputSection = document.getElementById('inputSection');
        this.errorMessage = document.getElementById('errorMessage');
        this.errorText = document.getElementById('errorText');
        this.successMessage = document.getElementById('successMessage');
        this.successText = document.getElementById('successText');

        this.currentImage = document.getElementById('currentImage');
        this.imagePlaceholder = document.getElementById('imagePlaceholder');
        this.currentText = document.getElementById('currentText');
        this.currentSceneCount = document.getElementById('currentScene');
        this.totalScenes = document.getElementById('totalScenes');
        this.sceneInfo = document.getElementById('sceneInfo');

        this.newStoryBtn = document.getElementById('newStoryBtn');
        this.downloadBtn = document.getElementById('downloadBtn');

        this.scenes = [];
        this.index = 0;
        this.zipDownloadUrl = null;

        if (this.form) {
            this.form.addEventListener('submit', (e) => this.generateStory(e));
        } else {
            console.warn('storyForm not found in DOM');
        }

        if (this.newStoryBtn) {
            this.newStoryBtn.addEventListener('click', () => this.resetUI());
        }

        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const playBtn = document.getElementById('playBtn');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.showPrev());
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.showNext());
        }
        if (playBtn) {
            playBtn.addEventListener('click', () => this.playCurrent());
        }

        if (this.downloadBtn) {
            this.downloadBtn.addEventListener('click', () => this.downloadStory());
        }
    }

    async generateStory(e) {
        e?.preventDefault();

        const prompt = this.promptEl?.value?.trim() || '';
        const desiredScenes = parseInt(this.scenesEl.value, 10) || 3;
        const ttsMode = this.ttsEl.value;

        if (!prompt) return this.showError('Please enter a prompt before generating.');

        this.setLoading(true, 'Generating story...');

        const url = (this.form && this.form.getAttribute('action')) ? this.form.getAttribute('action') : '/api/generate';

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, desired_scenes: desiredScenes, tts_mode: ttsMode })
            });

            if (!response.ok) {
                console.warn('Backend responded with non-OK status:', response.status);
                this.showDemo(prompt, desiredScenes);
                return;
            }

            const result = await response.json();

            if (result && result.success && result.data) {
                const data = result.data;

                if (data.short_texts && data.images_dataurls) {
                    this.scenes = [];
                    const maxScenes = Math.max(data.short_texts.length, data.images_dataurls.length);
                    
                    for (let i = 0; i < maxScenes; i++) {
                        this.scenes.push({
                            text: data.short_texts[i] || '',
                            image_url: data.images_dataurls[i] || null,
                            audio_url: data.audio_dataurls ? data.audio_dataurls[i] : null
                        });
                    }
                    
                    this.index = 0;
                    this.populateViewer();

                    if (data.zip_dataurl) {
                        this.zipDownloadUrl = data.zip_dataurl;
                    }
                    
                    this.showSuccess('Story generated successfully!');
                } else {
                    console.warn('Backend data missing expected fields, using demo fallback.');
                    this.showDemo(prompt, desiredScenes);
                }
            } else {
                console.warn('Backend returned unexpected format, using demo fallback.');
                this.showDemo(prompt, desiredScenes);
            }
        } catch (err) {
            console.error('Error while generating story:', err);
            this.showDemo(prompt, desiredScenes);
        } finally {
            this.setLoading(false);
        }
    }

    showDemo(prompt, desiredScenes) {
        this.scenes = [];
        for (let i = 1; i <= Math.max(2, desiredScenes); i++) {
            this.scenes.push({
                text: `Scene ${i}: A short scene based on your prompt — "${prompt.slice(0, 80)}"${prompt.length > 80 ? '…' : ''}`,
                image_url: null
            });
        }
        this.index = 0;
        this.populateViewer();
        this.showSuccess('Demo story generated (backend unavailable or returned unexpected data).');
    }

    populateViewer() {
        if (this.inputSection) this.inputSection.style.display = 'none';
        if (this.viewerSection) this.viewerSection.style.display = 'block';

        this.totalScenes.textContent = String(this.scenes.length);
        this.currentSceneCount.textContent = String(this.index + 1);
        this.updateSceneDisplay();
    }

    updateSceneDisplay() {
        const scene = this.scenes[this.index];
        if (!scene) return;

        if (this.currentText) {
            this.currentText.innerText = scene.text || '';
        }

        if (scene.image_url && this.currentImage) {
            this.currentImage.src = scene.image_url;
            this.currentImage.style.display = '';
            if (this.imagePlaceholder) this.imagePlaceholder.style.display = 'none';
        } else {
            if (this.currentImage) {
                this.currentImage.style.display = 'none';
            }
            if (this.imagePlaceholder) this.imagePlaceholder.style.display = 'flex';
        }

        if (this.sceneInfo) {
            this.sceneInfo.innerHTML = `Scenes: <strong>${this.scenes.length}</strong> — use Prev/Next to navigate.`;
        }
        if (this.currentSceneCount) this.currentSceneCount.textContent = String(this.index + 1);
        if (this.totalScenes) this.totalScenes.textContent = String(this.scenes.length);
    }

    showPrev() {
        if (this.index > 0) {
            this.index--;
            this.updateSceneDisplay();
        }
    }

    showNext() {
        if (this.index < this.scenes.length - 1) {
            this.index++;
            this.updateSceneDisplay();
        }
    }

    playCurrent() {
        const scene = this.scenes[this.index];
        if (!scene || !scene.text) return this.showError('No scene text to play.');

        if (scene.audio_url) {
            try {
                const audio = new Audio(scene.audio_url);
                audio.play().then(() => {
                    this.showSuccess('Playing scene audio.');
                }).catch(err => {
                    console.warn('Failed to play backend audio:', err);
                    this.fallbackToSpeechSynthesis(scene.text);
                });
                return;
            } catch (err) {
                console.warn('Backend audio failed:', err);
            }
        }

        this.fallbackToSpeechSynthesis(scene.text);
    }

    fallbackToSpeechSynthesis(text) {
        if ('speechSynthesis' in window) {
            const ut = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(ut);
            this.showSuccess('Playing scene with browser TTS.');
        } else {
            this.showError('Browser Speech Synthesis not available.');
        }
    }

    downloadStory() {
        if (this.zipDownloadUrl) {
            const link = document.createElement('a');
            link.href = this.zipDownloadUrl;
            link.download = 'story_files.zip';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            this.showSuccess('Download started!');
        } else {
            this.showError('No download available. Try generating a story first.');
        }
    }

    setLoading(isLoading, text = '') {
        if (this.loading) {
            this.loading.style.display = isLoading ? 'flex' : 'none';
        }
        if (this.loadingText && isLoading) {
            this.loadingText.textContent = text;
        }
    }

    resetUI() {
        // Reset to input form
        if (this.viewerSection) this.viewerSection.style.display = 'none';
        if (this.inputSection) this.inputSection.style.display = 'block';

        // Clear form if desired
        if (this.promptEl) this.promptEl.value = '';
        if (this.scenesEl) this.scenesEl.value = '3';

        // Clear internal state
        this.scenes = [];
        this.index = 0;
        this.zipDownloadUrl = null;

        this.hideMessages();
    }

    showError(message) {
        this.hideMessages();
        if (this.errorMessage && this.errorText) {
            this.errorText.textContent = message;
            this.errorMessage.style.display = 'block';
        }
    }

    showSuccess(message) {
        this.hideMessages();
        if (this.successMessage && this.successText) {
            this.successText.textContent = message;
            this.successMessage.style.display = 'block';
        }
    }

    hideMessages() {
        if (this.errorMessage) this.errorMessage.style.display = 'none';
        if (this.successMessage) this.successMessage.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.storyApp = new StoryApp();
});
