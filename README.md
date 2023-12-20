# llm-tgbot

This is a simple telegram bot interface that can perform tasks such as interacting with users using a chat model, clearing chat history, generating images, and transcribing voice messages.

## Features

- Chat interaction: The bot can interact with users using a chat model. Use the command `/clear` to clear the chat history.
- Generate images: The bot can generate images using OpenAI's DALL-E model upon receiving the command `/dalle`.
- Transcribe voice messages: The bot can transcribe voice messages and provide the transcription in the chat.

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

[MIT](https://choosealicense.com/licenses/mit/)
