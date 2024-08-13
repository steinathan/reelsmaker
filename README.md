> 🔥 I indend to turn this into a full-fleged project in the future, please contact me if you want to collaborate.

## ReelsMaker

ReelsMaker is a Python-based/streamlit application designed to create captivating faceless videos for social media platforms like TikTok and YouTube.

### Examples

https://github.com/user-attachments/assets/e65f70a9-8412-4b74-b11b-1009722831bc

https://github.com/user-attachments/assets/aff6b1fb-fd55-4411-bb07-20d65a14ee60

https://github.com/user-attachments/assets/bd1d4948-6a54-45c6-b121-ffd064c7419f

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

This project is licensed under the MIT License - see the LICENSE file for details
