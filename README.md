# Frontend repository link
https://github.com/AlikhanNasa7/Higgsfield-SWE-Hackaton

# Higgsfield Backend API

Production-ready chat-based assistant backend with Higgsfield generation integration. This system provides a robust API for managing chats, generating media (images/videos) via Higgsfield's models, and handling async job polling with proper idempotency and reliability guarantees.
## Architecture

graph TD
    Client[Browser/Client] -->|HTTP| API[FastAPI Backend]
    
    subgraph Backend
        API --> Routes[API Routes]
        Routes -->|Image Gen| HF_IMG[Text2Image Service]
        Routes -->|Video Gen| HF_VID[Text2Video Service]
        Routes -->|Image2Vid| HF_I2V[Image2Video Service]
        
        HF_IMG --> HF[Higgsfield AI Platform]
        HF_VID --> HF
        HF_I2V --> HF
        
        Routes -->|Chat/Messages| DB[(PostgreSQL)]
        Routes -->|File Upload| S3[S3 Storage]
        
        subgraph Services
            HF_IMG
            HF_VID
            HF_I2V
            Chat[Chat Service]
            Claude[Claude Recommender]
        end
        
        Routes --> Chat
        Chat --> Claude
        Claude --> DB
    end
    
    subgraph "Async Operations"
        HF -->|Job Status| Polling[Status Polling]
        Polling -->|Updates| Routes
    end
    
    subgraph "Storage Layer"
        DB
        S3
    end


## 🚀 Features

- Text to Image generation
- Text to Video generation
- Image to Video transformation
- Multiple AI model support:
  - Seedance
  - Minimax
  - Kling
  - Wan-25
  - Nano Banana
  - Seedream

## 🛠 Tech Stack

- FastAPI
- SQLAlchemy (async)
- Alembic
- Python 3.12+
- Docker
- PostgreSQL



## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Higgsfield API credentials

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Higgsfield credentials
# HIGGSFIELD_API_KEY=your_key_here
# HIGGSFIELD_SECRET=your_secret_here
```

### 2. Start Services

```bash
# Start all services (postgres, redis, localstack, api, worker)
make dev-up

# This will:
# - Start Docker Compose services
# - Run database migrations
# - Initialize LocalStack S3 bucket with CORS
```

### 3. Verify

```bash
# Check health
curl http://localhost:8000/healthz

# View API docs
open http://localhost:8000/docs

```

### 4. Stop Services

```bash
make dev-down
```


## 📦 Project Structure

```
backend/
├── alembic/                    # Database migrations
│   └── versions/               # Migration versions
├── app/
│   ├── api/
│   │   ├── higgsfield/        # Higgsfield AI Integration
│   │   │   ├── text2image.py  # Image generation
│   │   │   ├── text2video.py  # Video generation
│   │   │   ├── image2video.py # Image to video conversion
│   │   │   ├── generate.py    # Universal generation
│   │   │   └── misc.py        # Utilities
│   │   ├── routes/
│   │   │   ├── chats.py       # Chat CRUD
│   │   │   ├── messages.py    # Message handling
│   │   │   ├── options.py     # Options management
│   │   │   ├── attachments.py # File attachments
│   │   │   └── health.py      # Health checks
│   │   ├── deps.py            # FastAPI dependencies
│   │   └── errors.py          # Error handling
│   ├── core/
│   │   ├── config.py          # Environment configuration
│   │   ├── logging.py         # Logging setup
│   │   └── security.py        # Authentication
│   ├── domain/
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # API schemas
│   │   ├── states.py          # System states
│   │   └── pagination.py      # Pagination utils
│   ├── services/
│   │   ├── chat_service.py    # Chat logic
│   │   ├── claude_recommender.py # AI recommendations
│   │   ├── response_parser.py # Response handling
│   │   └── attachments.py     # File handling
│   ├── infra/
│   │   ├── db.py             # Database connection
│   │   └── s3.py             # S3 storage
│   ├── image_styles.json     # Image style configs
│   ├── motions.json         # Video motion configs
│   └── main.py              # Application entry
```



## 💻 API Usage

### Image to Video Generation

```python
POST /higgsfield/image2video/generate

# Request body example:
{
  "params": {
    "model_name": "seedance",  # Options: seedance, kling-2-5, minimax, wan-25-fast
    "prompt": "A cinematic portrait",
    "input_image": {
      "type": "image_url",
      "image_url": "https://example.com/image.jpg"
    },
    "duration": 5,
    "enhance_prompt": true
  }
}
```

### Supported Models

#### Seedance Pro
- High-quality video generation
- Resolution: 1080p
- Duration: 5-10 seconds
- Supports prompt enhancement

#### Kling v2.5 Turbo
- Fast video generation
- Custom model parameters
- Enhanced prompt processing

#### Minimax
- Fixed 6-second duration
- 768p resolution
- Supports start and end image inputs

#### Wan-25-Fast
- Quick video generation
- 720p resolution
- Supports negative prompts
- Optional audio input

## 🔑 Environment Variables

```env
HIGGSFIELD_API_KEY=your_api_key
HIGGSFIELD_SECRET=your_secret
DATABASE_URL=sqlite:///./sql_app.db
```

## 🧪 Running Tests

```bash
pytest
```

## 📝 License

[License Type] - See LICENSE file for details

## 👥 Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## 🐛 Known Issues

- Some models may return failed status without detailed error messages
- Webhook implementation is in progress

## 🔜 Roadmap

- [ ] Add more detailed error handling
- [ ] Implement webhook notifications
- [ ] Add support for batch processing
- [ ] Improve documentation

## 📄 License

MIT License - See LICENSE file for details.

---

**Authors: Alikhan Nashtay, Adilet Shildebayev, Edige Akimali, Dinmukhamed Albek**


**Built with ❤️ for the Higgsfield platform**
