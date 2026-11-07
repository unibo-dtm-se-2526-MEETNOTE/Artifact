# MeetNote

MeetNote is a desktop application that helps administrators turn recorded
meetings into reviewable and trackable action items.

It provides a Kivy-based interface for uploading meeting recordings,
transcribing them, generating candidate action items, reviewing them, and
managing approved items on a task board.

## Features

- Desktop user interface built with Kivy.
- Local transcription of meeting recordings using faster-whisper.
- AI-assisted extraction of candidate action items using Google Gemini.
- Administrative review workflow for action items.
- Status transitions for proposed, approved, rejected, and completed items.
- Task board for managing verified action items.
- Poetry-based dependency management.
- Automated tests, coverage reporting, and static analysis.

## Requirements

- Python 3.11, 3.12, or 3.13
- Poetry
- A Google Gemini API key
- Optional: ffmpeg, if required by your local audio/video setup

## Installation

Clone the repository:

```bash
git clone [https://github.com/unibo-dtm-se-2526-MEETNOTE/Artifact.git](https://github.com/unibo-dtm-se-2526-MEETNOTE/Artifact.git)
cd Artifact
```

Install the base dependencies:

```bash
py -3.12 -m poetry install
```

To include local transcription support, install the optional `whisper`
dependency group:

```bash
py -3.12 -m poetry install --with whisper
```

## Configuration

MeetNote requires a Google Gemini API key to generate action items from
meeting transcripts.

Create a `.env` file in the repository root:

```env
GEMINI_API_KEY=your_google_gemini_api_key
```

Do not commit `.env`, API keys, or other secrets to the repository.

## Running the application

Start MeetNote with:

```bash
py -3.12 -m poetry run python -m meetnote
```

## Development commands

Run the test suite:

```bash
py -3.12 -m poetry run poe test
```

Run static checks:

```bash
py -3.12 -m poetry run poe static-checks
```

Run Ruff checks:

```bash
py -3.12 -m poetry run poe ruff-check
```

Automatically fix straightforward Ruff issues:

```bash
py -3.12 -m poetry run poe ruff-fix
```

Format the code:

```bash
py -3.12 -m poetry run poe format
```

Run type checking:

```bash
py -3.12 -m poetry run poe mypy
```

Measure test coverage:

```bash
py -3.12 -m poetry run poe coverage
py -3.12 -m poetry run poe coverage-report
```

Generate an HTML coverage report:

```bash
py -3.12 -m poetry run poe coverage-html
```

## Project structure

```text
meetnote/
├── core/          # Domain models and business rules
├── services/      # Application services and orchestration
├── adapters/      # External service integrations
├── persistence/   # Data storage and repositories
├── ui/            # Kivy user interface
└── __main__.py    # Application entry point

tests/             # Automated tests
.github/workflows/ # CI/CD workflows
```

## Application workflow

1. Upload an audio or video meeting recording.
2. Transcribe the recording locally using faster-whisper.
3. Extract candidate action items using Google Gemini.
4. Review each candidate action item.
5. Approve, edit, reject, or request changes.
6. Manage approved items on the task board.

## Contributing

Before opening a pull request:

1. Create a descriptive feature or fix branch.
2. Make your changes.
3. Add or update tests where appropriate.
4. Run the tests and static checks.
5. Use Conventional Commits for commit messages.

Examples:

```bash
git commit -m "feat: add meeting recording upload screen"
git commit -m "fix: validate Gemini API key before extractor initialization"
git commit -m "test: add action item status transition tests"
git commit -m "docs: update project README"
```

## License

This project is distributed under the Apache License 2.0.