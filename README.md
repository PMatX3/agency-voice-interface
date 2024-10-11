# Realtime API Async Python Assistant

This project demonstrates the use of OpenAI's Realtime API to create an AI assistant capable of handling voice input, performing various tasks, and providing audio responses. It showcases the integration of tools, structured output responses, and real-time interaction.

## Features

- Real-time voice interaction with an AI assistant
- Integration with OpenAI's GPT-4o Realtime API
- Asynchronous audio input and output handling
- Custom function execution based on user requests
- ChatGPT-like visual interface for audio volume visualization
- Structured output processing
- File management capabilities (create, update, delete)
- Browser interaction
- Task delegation to AI agents

## Setup

1. Install [uv](https://docs.astral.sh/uv/), the modern Python package manager.
2. Clone this repository.
3. Copy the sample environment file: `cp .env.sample .env`
4. Add your `OPENAI_API_KEY` to the `.env` file.
5. Update `personalization.json` with your preferred settings.
6. Install dependencies: `uv sync`
7. Run the assistant: `uv run main`

## Usage

Once the assistant is running, you can interact with it using voice commands. Here are some example interactions:

1. "What's the current time?"
2. "Generate a random number."
3. "Open ChatGPT in the browser."
4. "Create a new file called user_data.txt with some sample content."
5. "Update the user_data.txt file, add more information."
6. "Delete the user_data.txt file."

## Code Structure

### Main Components

- `main.py`: Entry point of the application, sets up the WebSocket connection and manages the main event loop.
- `functions.py`: Contains definitions for various functions that can be called by the AI assistant.
- `models.py`: Defines Pydantic models for structured data handling.
- `config.py`: Manages configuration settings and environment variables.
- `utils.py`: Provides utility functions for logging, encoding, and prompting.
- `visual_interface.py`: Implements a visual interface for audio energy visualization.
- `websocket_handler.py`: Handles WebSocket events and message processing.
- `agency_functions.py`: Defines virtual agents for task delegation.

### Key Features

1. **Asynchronous WebSocket Communication**:
   The application uses `websockets` to establish an asynchronous connection with the OpenAI Realtime API.

2. **Audio Input/Output Handling**:
   The `AsyncMicrophone` class manages real-time audio capture, while the `play_audio` function handles audio playback.

3. **Function Execution**:
   Custom functions are defined in `functions.py` and can be called by the AI assistant based on user requests.

4. **Structured Output Processing**:
   The application uses Pydantic models to handle structured data responses from the AI.

5. **Visual Interface**:
   A PyGame-based visual interface provides real-time visualization of current audio volume.

6. **Agency Functions**:
   The project includes a basic implementation of AI agents for task delegation.


## Configuration

The project uses environment variables and a `personalization.json` file for configuration. Ensure that you have set up the following:

- `OPENAI_API_KEY`: Your OpenAI API key
- `PERSONALIZATION_FILE`: Path to your personalization JSON file
- `SCRATCH_PAD_DIR`: Directory for temporary file storage

## Improvements and Future Work

- Implement interruption handling for smoother conversation flow.
- Add transcript logging for better conversation tracking.
- Convert `personalization.json` to a Pydantic model for improved type safety.
- Implement parallel execution of tools for increased efficiency.
- Fix audio cutoff issues near the end of responses.
- Enhance error handling and recovery mechanisms.
- Implement more sophisticated turn-taking algorithms.

## Resources

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)
- [WebSockets Library for Python](https://websockets.readthedocs.io/)
- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- [Pygame Documentation](https://www.pygame.org/docs/)
