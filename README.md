> 🔥 I indend to turn this into a full-fleged project in the future, please contact me if you want to collaborate.

## ReelsMaker

ReelsMaker is a Python-based/streamlit application designed to create captivating faceless videos for social media platforms like TikTok and YouTube.

### Examples

<video src='examples/example1.mp4' />
<video src='examples/example2.mp4' />
<video src='examples/example3.mp4' />

### Features

- AI-Powered Prompt Generation: Automatically generate creative prompts for your video content.
- Subtitles Generation: Auto-generate subtitles using the subtitle_gen.py module.
- Text-to-Speech with TikTok or elevenlabs Voices: Use the tiktokvoice or elevenlabs to add synthetic voices to your videos.

## Installation

```sh
git clone https://github.com/steinathan/reelsmaker.git
cd reelsmaker
```

create a virtual environment and install

```sh
$ poetry shell
$ poetry install
```

copy and update the `.env`

```sh
$ cp .env.example .env
```

start the application

```sh
$ streamlit run reelsmaker.py
```

### Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

### License

This project is licensed under the MIT License - see the LICENSE file for details.
