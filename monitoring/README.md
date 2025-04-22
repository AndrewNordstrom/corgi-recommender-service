# Monitoring Setup for Corgi Recommender Service

This directory contains configuration files for monitoring the Corgi Recommender Service using Prometheus and Grafana.

## Overview

The monitoring stack consists of:

1. **Prometheus**: Collects metrics from the Corgi Recommender Service
2. **Grafana**: Visualizes the metrics with pre-built dashboards

## Key Metrics

The Corgi Recommender Service exposes the following metrics:

- **Injection Metrics**:
  - `corgi_injected_posts_total`: Total number of posts injected into timelines
  - `corgi_injection_ratio`: Ratio of injected posts to total posts in timeline
  - `corgi_injection_processing_time_seconds`: Time taken to process timeline injection

- **Recommendation Metrics**:
  - `corgi_recommendations_total`: Total number of recommendations generated
  - `corgi_recommendation_scores`: Distribution of recommendation scores
  - `corgi_recommendation_processing_time_seconds`: Time taken to generate recommendations
  - `corgi_fallback_usage_total`: Number of times the system fell back to cold start
  - `corgi_recommendation_interactions_total`: User interactions with recommended posts
  
- **Timeline Metrics**:
  - `corgi_timeline_post_count`: Number of real vs. injected posts in timeline responses

## Setup

### Starting the Monitoring Stack

```bash
docker-compose -f docker-compose-monitoring.yml up -d
```

### Accessing Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Username: admin
  - Password: corgi

### Default Dashboard

The monitoring setup comes with a pre-configured dashboard for Corgi Recommender Service metrics:

- **Corgi Recommender Dashboard**: Provides an overview of recommendation and injection metrics

## Configuration Files

- **Prometheus**:
  - `prometheus/prometheus.yml`: Main Prometheus configuration

- **Grafana**:
  - `grafana/provisioning/datasources/prometheus.yml`: Datasource configuration
  - `grafana/provisioning/dashboards/dashboards.yml`: Dashboard loading configuration
  - `grafana/dashboards/corgi-dashboard.json`: Pre-built dashboard for Corgi metrics

## Troubleshooting

If metrics aren't showing up:

1. Check if the Corgi service is running and exposing metrics on port 9100
2. Verify that Prometheus can reach the Corgi service (check `host.docker.internal` DNS resolution)
3. Check Prometheus targets at http://localhost:9090/targets to see if scraping is successful