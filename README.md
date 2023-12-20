# llm-tgbot

This is a simple telegram bot interface that can perform tasks such as interacting with users using a chat model, clearing chat history, generating images, and transcribing voice messages.

## Features

- **Chat Interaction**: The bot can interact with users using a chat model, with supports of streaming and markdown rendering. Use the command `/clear` to clear the chat history.
- **Image Generation**: The bot can generate images using OpenAI's DALL-E model upon receiving the command `/dalle`.
- **Voice Message Transcription**: The bot can transcribe voice messages and provide the transcription in the chat. The transcriptions can also be used to perform queries for chat or image generation.

## Installation

1. Clone the repository.
2. Install the required packages using pip:

    ```sh
    pip install -r requirements.txt
    ```

3. Set up the environment variables. You can use the provided [`.env.example`](.env.example) file as a template. Rename it to `.env` and fill in your values.

## Usage

Run the bot using the command:

```sh
python bot.py
```

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).
