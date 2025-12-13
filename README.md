# Trip Me Buddy

An enterprise-grade AI-powered travel planning platform demonstrating production-ready architecture.

## Overview

Trip Me Buddy is a comprehensive travel planning application that leverages agentic AI to help users plan their trips. The platform integrates flight search, hotel recommendations, and activity suggestions into a seamless user experience.

## Architecture

- **Frontend**: React 18 with TypeScript, Material-UI
- **Backend**: FastAPI with Python 3.11+
- **AI Agents**: LangGraph orchestration with Gemini API
- **Authentication**: Keycloak (OAuth 2.0, RBAC)
- **Database**: PostgreSQL on AWS RDS
- **Caching**: Redis on AWS ElastiCache
- **Data Warehouse**: Amazon Redshift with AWS Glue ETL
- **Analytics**: Power BI dashboards
- **Infrastructure**: AWS (ECS Fargate, VPC, ALB, S3, CloudFront)
- **IaC**: Terraform
- **External APIs**: Amadeus Self-Service API

## Key Features

- AI-powered trip planning with multi-agent system
- Real-time flight, hotel, and activity recommendations
- User authentication and authorization
- Trip history and saved preferences
- Enterprise-grade security and compliance (GDPR, DPDP)
- Production-ready data pipeline and analytics

## Development Timeline

**Phase 1 (Weeks 1-3)**: Foundation & Infrastructure
- AWS setup, Keycloak, Redis, Backend & Frontend foundation

**Phase 2 (Weeks 4-6)**: AI Agents & Travel Integration
- LangGraph agents, Amadeus API, Travel search implementation

**Phase 3 (Weeks 7-9)**: Data Pipeline & Analytics
- Redshift, AWS Glue ETL, Power BI dashboards

**Phase 4 (Weeks 10-12)**: Production & Polish
- Advanced features, testing, deployment, documentation

## Project Structure

```
trip-me-buddy/
├── frontend/          # React application
├── backend/           # FastAPI service
├── infrastructure/    # Terraform IaC
├── docs/              # Documentation
└── README.md          # This file
```

## Getting Started

Documentation for setup and development is in the `docs/` folder.

## Cost Estimation

- Development: $45-60/month (optimized)
- Production: $120-125/month

## Author

Swapnil - Enterprise AI & Cloud Architecture Portfolio Project

## License

Private - Portfolio/Demonstration Project
