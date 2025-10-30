# Content Automation Platform

## Overview

This is a Flask-based content automation platform that enables users to generate, manage, schedule, and analyze social media content across multiple platforms. The system leverages OpenAI's GPT models for intelligent content generation and provides a comprehensive dashboard for content management. Key features include template-based content generation, multi-platform scheduling, analytics tracking, and platform connection management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Bootstrap dark theme for responsive UI
- **Static Assets**: Custom CSS and JavaScript files for enhanced user experience
- **Pages**: Modular template structure with base template inheritance for consistent layout
- **Client-Side Libraries**: Chart.js for analytics visualization, Font Awesome for icons

### Backend Architecture
- **Web Framework**: Flask with SQLAlchemy ORM for database operations
- **Application Structure**: Modular design with separated concerns:
  - `app.py`: Application factory and database initialization
  - `routes.py`: Request handling and API endpoints
  - `models.py`: Database schema definitions
  - `content_generator.py`: AI-powered content generation logic
  - `scheduler.py`: Background job scheduling for automated posting

### Data Storage
- **Database**: SQLite by default with configurable DATABASE_URL for PostgreSQL support
- **ORM**: SQLAlchemy with DeclarativeBase for modern Python database operations
- **Connection Pooling**: Configured with pool recycling and pre-ping for reliability
- **Schema**: Four main entities:
  - ContentTemplate: Reusable content templates
  - GeneratedContent: AI-generated content with status tracking
  - PlatformConnection: Social platform integration status
  - PostAnalytics: Performance metrics and engagement data

### Content Generation System
- **AI Integration**: OpenAI GPT-5 model for intelligent content creation
- **Template System**: Customizable content templates for different platforms and use cases
- **Platform Optimization**: Content tailored for Twitter, Facebook, Instagram, LinkedIn, and blog platforms
- **Response Format**: Structured JSON output with title, content, and hashtags

### Scheduling and Automation
- **Background Scheduler**: APScheduler for automated content publishing
- **Job Management**: Individual job tracking with cancellation capabilities
- **Status Tracking**: Content lifecycle management (draft, scheduled, published, failed)
- **Time-based Triggers**: Precise scheduling with timezone support

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web framework with SQLAlchemy integration
- **Werkzeug**: WSGI utilities including ProxyFix for deployment

### AI and Content Generation
- **OpenAI API**: GPT-5 model integration for content generation
- **API Key Management**: Environment-based configuration for secure API access

### Scheduling and Background Tasks
- **APScheduler**: Advanced Python Scheduler for automated content publishing
- **Background Processing**: Non-blocking job execution for scheduled posts

### Database and Storage
- **SQLAlchemy**: ORM with support for SQLite (default) and PostgreSQL
- **Database Configuration**: Environment-based connection string management

### Frontend Libraries
- **Bootstrap**: Replit dark theme variant for consistent UI
- **Chart.js**: Analytics dashboard visualization
- **Font Awesome**: Icon library for enhanced user interface

### Development and Deployment
- **Environment Variables**: Configuration management for secrets and settings
- **Logging**: Built-in Python logging for debugging and monitoring
- **Session Management**: Flask session handling with configurable secret keys