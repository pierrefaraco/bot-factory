# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Angular 18 application called "AlfredReact" that appears to be a bot creation and management platform. The application includes user authentication, bot customization, chat functionality, and administrative features.

## Development Commands

### Core Development
- `npm start` - Start development server on host 0.0.0.0:4200
- `ng serve` - Alternative development server (localhost:4200)
- `ng build` - Build the project (outputs to dist/)
- `ng build --watch --configuration development` - Build with watch mode
- `ng test` - Run unit tests via Karma

### Angular CLI Commands
- `ng generate component component-name` - Generate new component
- `ng generate directive|pipe|service|class|guard|interface|enum|module` - Generate other Angular artifacts

## Architecture Overview

### Core Structure
- **Frontend**: Angular 18 with TypeScript
- **Styling**: Bootstrap 5 + Custom SCSS themes (dark/light)
- **Authentication**: JWT-based with custom interceptors
- **State Management**: Angular services with RxJS
- **UI Components**: Custom component library with reusable base components

### Key Directories
- `src/app/components/` - Feature components (admin, bot-list, chat, etc.)
- `src/app/components/base/` - Reusable UI components (button, form-field, dialog, etc.)
- `src/app/services/` - Business logic and API services
- `src/app/models/` - TypeScript interfaces and data models
- `src/app/guards/` - Route protection (auth.guard.ts)
- `src/app/interceptors/` - HTTP interceptors for JWT and error handling

### Main Features
- **Authentication**: Login/register with JWT tokens
- **Bot Management**: Create, customize, and manage bots with visual avatar builder
- **Chat System**: Real-time communication with bots
- **Admin Panel**: User management and system administration
- **Data Management**: Import/export functionality
- **Theming**: Dynamic dark/light theme switching

### Important Files
- `src/app/app.config.ts` - Application configuration with providers
- `src/app/app.routes.ts` - Route definitions (currently auth guards commented out)
- `src/app/interceptors/jwt.interceptor.ts` - JWT and error handling
- `src/styles/` - Theme files (dark-theme.scss, light-theme.scss)

### Dependencies
- Angular 18 with Material Design and Bootstrap
- JWT handling with jwt-decode
- WebSocket support via event-source-polyfill
- UUID generation for unique identifiers

## Development Notes

The application uses a custom theme system with both dark and light modes. The routing currently has authentication guards commented out, suggesting the app may be in development mode for easier testing.

The bot creation system includes a sophisticated avatar builder with SVG components for customizing bot appearance (eyes, mouth, hat, colors).