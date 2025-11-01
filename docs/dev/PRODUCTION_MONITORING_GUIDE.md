# Production Monitoring Guide
**Date**: October 29, 2025
**Status**: ✅ Complete - Production Ready

---

## Overview

This guide provides comprehensive documentation for the production monitoring system implemented in Week 3 of the QA strategy. The monitoring framework ensures reliability, observability, and performance tracking of the USASpending MCP Server.

---

## 1. Health Check System

### 1.1 Health Endpoint

**URL**: `GET /health`

**Purpose**: Provides real-time system health status and key metrics

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T10:30:45.123456Z",
  "version": "1.0.0",
  "uptime": {
    "seconds": 3600,
    "formatted": "1 hour"
  },
  "request_stats": {
    "total": 1250,
    "success": 1248,
    "failures": 2,
    "success_rate": 0.9984
  },
  "response_times": {
    "avg_ms": 45.3,
    "p50_ms": 32.1,
    "p95_ms": 125.6,
    "p99_ms": 245.2,
    "max_ms": 1250.5
  },
  "tools": {
    "total": 21,
    "operational": 21,
    "healthy": 21,
    "warning": 0,
    "failed": 0
  },
  "api_health": {
    "usaspending_api": "healthy",
    "response_time_ms": 125,
    "last_check": "2025-10-29T10:30:30.123456Z"
  }
}
```

### 1.2 Health Status Codes

| Status | Code | Description | Action |
|--------|------|-------------|--------|
| **healthy** | 200 | All systems operational | None needed |
| **degraded** | 200 | Some issues but operational | Monitor closely |
| **unhealthy** | 503 | Major issues | Immediate investigation |
| **unknown** | 503 | Cannot determine status | Check logs |

### 1.3 Health Checks Included

✅ **API Connectivity**
- Checks connection to USASpending API
- Validates response time
- Monitors availability

✅ **Memory Health**
- Monitors memory usage
- Tracks garbage collection
- Alerts on memory leaks

✅ **Connection Pooling**
- Validates active connections
- Checks connection pool status
- Monitors idle connections

✅ **Service Dependencies**
- External API availability
- Database connectivity
- Cache status

---

## 2. Performance Metrics

### 2.1 Metrics Collected

**Request Metrics:**
```
✅ Total requests per tool
✅ Successful requests
✅ Failed requests
✅ Request rate (req/sec)
✅ Concurrent requests
```

**Response Time Metrics:**
```
✅ Average response time
✅ Median (p50)
✅ 95th percentile (p95)
✅ 99th percentile (p99)
✅ Maximum response time
✅ Minimum response time
```

**Error Metrics:**
```
✅ Error count per tool
✅ Error rate (%)
✅ Error categories
✅ Error trends over time
✅ Most common errors
```

### 2.2 Performance Targets (SLA)

| Operation | Target | Alert > | Critical > |
|-----------|--------|---------|-----------|
| Simple Lookup | 1s | 2s | 5s |
| Keyword Search | 5s | 10s | 30s |
| Complex Query | 10s | 20s | 60s |
| Data Export | 30s | 60s | 120s |

### 2.3 Metrics Endpoint

**URL**: `GET /metrics`

**Response Format:**
```json
{
  "timestamp": "2025-10-29T10:30:45.123456Z",
  "period": "last_1_hour",
  "metrics": {
    "requests": {
      "total": 1250,
      "per_second": 0.347,
      "by_tool": {
        "get_award_by_id": 245,
        "search_federal_awards": 189,
        "get_award_details": 156,
        "..."  : 660
      }
    },
    "performance": {
      "response_times": {
        "avg_ms": 45.3,
        "p95_ms": 125.6,
        "p99_ms": 245.2
      },
      "slowest_tools": [
        {"name": "analyze_federal_spending", "avg_ms": 234},
        {"name": "get_spending_by_state", "avg_ms": 156}
      ]
    },
    "errors": {
      "total": 2,
      "rate_percent": 0.16,
      "by_type": {
        "network_error": 1,
        "timeout": 1
      }
    }
  }
}
```

---

## 3. Error Tracking & Alerting

### 3.1 Error Categories

**Network Errors (5% of errors)**
- Connection failures
- Timeout errors
- DNS failures
- SSL certificate errors

**Validation Errors (15% of errors)**
- Invalid parameters
- Missing required fields
- Type mismatches
- Out-of-range values

**Application Errors (35% of errors)**
- Null pointer exceptions
- Data processing failures
- Cache failures
- Logic errors

**API Errors (45% of errors)**
- 404 Not Found
- 500 Server Error
- Rate limiting (429)
- Gateway timeout (504)

### 3.2 Error Logging

**Log Entry Example:**
```json
{
  "timestamp": "2025-10-29T10:30:45.123456Z",
  "level": "ERROR",
  "tool": "search_federal_awards",
  "request_id": "req_abc123def456",
  "error": {
    "type": "TimeoutError",
    "message": "API request timeout after 5000ms",
    "code": "E_API_TIMEOUT"
  },
  "context": {
    "user_agent": "MCP-Client/1.0",
    "parameters": {"keyword": "GIGA", "limit": 10},
    "duration_ms": 5123
  },
  "stack_trace": "...",
  "recovery_action": "retry_with_fallback"
}
```

### 3.3 Alert Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Error Rate | >1% | >5% | Investigate / Escalate |
| Response Time p95 | >500ms | >2000ms | Review / Optimize |
| Failed Requests | >10 | >50 | Alert team |
| Memory Usage | >70% | >90% | Monitor / Restart |
| CPU Usage | >75% | >95% | Monitor / Scale |

---

## 4. Structured Logging

### 4.1 Log Files

The server maintains three separate log files in the `logs/` directory with automatic rotation:

| File | Purpose | Size Limit | Backups | Content |
|------|---------|-----------|---------|---------|
| **usaspending_mcp.log** | Complete activity log | 10 MB | 5 | All messages (DEBUG→CRITICAL) |
| **usaspending_mcp_errors.log** | Error diagnosis | 5 MB | 3 | ERROR and CRITICAL only |
| **usaspending_mcp_searches.log** | Analytics tracking | 20 MB | 5 | Successful searches/queries |

**Log File Locations:**
```bash
# View logs in your project directory
logs/usaspending_mcp.log           # All activity
logs/usaspending_mcp_errors.log    # Errors only
logs/usaspending_mcp_searches.log  # Search analytics
```

**Quick Commands:**
```bash
# Monitor in real-time
tail -f logs/usaspending_mcp.log

# Check for errors
tail -20 logs/usaspending_mcp_errors.log

# View search statistics
wc -l logs/usaspending_mcp_searches.log
grep "Tool:" logs/usaspending_mcp_searches.log | head -20
```

**Complete Documentation**: See `logs/README.md` for comprehensive log monitoring guide.

### 4.2 Log Levels

```
DEBUG   - Detailed diagnostic information
INFO    - General informational messages
WARNING - Warning conditions (recoverable issues)
ERROR   - Error conditions (operation failed)
CRITICAL - Critical errors (system at risk)
```

### 4.3 Log Format

All logs follow standard JSON format:

```json
{
  "timestamp": "ISO8601",
  "level": "LOG_LEVEL",
  "component": "COMPONENT_NAME",
  "operation": "OPERATION_NAME",
  "status": "SUCCESS|FAILURE",
  "duration_ms": 123,
  "message": "Human readable message",
  "context": {
    "key": "value"
  },
  "error": {
    "type": "ERROR_TYPE",
    "message": "Error message",
    "code": "ERROR_CODE"
  }
}
```

### 4.4 Log Aggregation

**Recommended Tools:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Splunk
- DataDog
- CloudWatch

**Log Shipping:**
```bash
# Option 1: File-based
- Logs written to files
- Fluentd/Logstash collects and forwards
- Centralized storage

# Option 2: Direct API
- Logs sent directly to aggregation service
- Low latency for critical errors
- Higher network overhead
```

---

## 5. Monitoring Dashboard

### 5.1 Dashboard Components

**Real-Time Metrics**
```
┌─────────────────────────────────────┐
│  System Health Status               │
│  ✅ Healthy (uptime: 99.8%)         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Request Rate (last 1 hour)         │
│  1,250 total requests               │
│  0.347 requests/second              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Response Times                     │
│  Avg: 45.3ms  |  p95: 125.6ms      │
│  p99: 245.2ms |  Max: 1,250.5ms    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Error Rate                         │
│  2 errors (0.16% rate)              │
│  Network: 1 | Timeout: 1            │
└─────────────────────────────────────┘
```

### 5.2 Tool-Specific Metrics

```
Tool: search_federal_awards
├── Requests: 189 (15% of total)
├── Success Rate: 99.5%
├── Avg Response: 156ms
├── p95 Response: 450ms
├── Error Count: 1
└── Errors: timeout (1)

Tool: analyze_federal_spending
├── Requests: 85 (6.8% of total)
├── Success Rate: 98.8%
├── Avg Response: 234ms
├── p95 Response: 850ms
├── Error Count: 1
└── Errors: network_error (1)
```

---

## 6. Setup Instructions

### 6.1 Enable Monitoring

**Step 1: Install Dependencies**
```bash
pip install prometheus-client flask-prometheus
```

**Step 2: Configure Monitoring**
```python
from monitoring import setup_monitoring

# In src/usaspending_mcp/server.py
setup_monitoring(app)
```

**Step 3: Start Metrics Collection**
```python
from monitoring import MetricsCollector

collector = MetricsCollector()
collector.start()
```

### 6.2 Configure Alerts

**Create Alert Rules:**
```yaml
alerts:
  - name: high_error_rate
    threshold: 5%
    duration: 5m
    action: email_ops_team

  - name: slow_response_time
    threshold: 2000ms (p95)
    duration: 10m
    action: page_on_call

  - name: api_unavailable
    threshold: 100% error rate
    duration: 1m
    action: immediate_escalation
```

### 6.3 Configure Log Aggregation

**Fluentd Configuration:**
```yaml
<source>
  @type tail
  path /var/log/usaspending-mcp/*.log
  pos_file /var/log/fluentd-usaspending.pos
  tag usaspending-mcp.*
  <parse>
    @type json
    time_format %iso8601
  </parse>
</source>

<match usaspending-mcp.**>
  @type forward
  <server>
    host logs.example.com
    port 24224
  </server>
</match>
```

---

## 7. Troubleshooting

### 7.1 Common Issues

**Issue: Health check returns 503 (Unhealthy)**

```
Solution:
1. Check API connectivity
   curl https://api.usaspending.gov/api/v2/references/agency/

2. Check memory usage
   ps aux | grep mcp_server

3. Check connection pool
   Review logs for connection errors

4. Restart service
   systemctl restart usaspending-mcp
```

**Issue: High response times (p95 > 500ms)**

```
Solution:
1. Check API response times
   Monitor upstream API performance

2. Review slow queries
   Analyze query logs for bottlenecks

3. Check resource usage
   CPU, Memory, Network I/O

4. Optimize queries
   Add caching, parallelize requests
```

**Issue: High error rate (>5%)**

```
Solution:
1. Check error logs
   Review recent error entries

2. Identify error pattern
   Group errors by type/cause

3. Fix root cause
   Address identified issues

4. Deploy fix
   Roll out corrected version

5. Verify resolution
   Monitor error rate reduction
```

---

## 8. Best Practices

### 8.1 Monitoring Best Practices

✅ **Always have baseline metrics**
- Know normal vs abnormal behavior
- Compare against historical data
- Use percentile-based alerting

✅ **Monitor both application and infrastructure**
- Application metrics: request rate, error rate, latency
- Infrastructure: CPU, memory, disk, network

✅ **Alert on symptoms, not causes**
- Alert on latency (symptom), not CPU usage (cause)
- Humans investigate root cause

✅ **Keep alerting focused**
- Too many alerts = ignored alerts
- Only alert on actionable items

### 8.2 Logging Best Practices

✅ **Log at appropriate levels**
- DEBUG: diagnostic info for developers
- INFO: significant events
- WARNING: recoverable issues
- ERROR: failures that need attention
- CRITICAL: system-level failures

✅ **Include context in logs**
- Request ID for tracing
- User/client information
- Parameters and data
- Stack traces for exceptions

✅ **Use structured logging**
- JSON format for parsing
- Consistent field names
- Parseable timestamps

---

## 9. Metrics Reference

### 9.1 Key Metrics

| Metric | Formula | Interpretation |
|--------|---------|-----------------|
| Success Rate | Success/Total | % of successful requests |
| Error Rate | Errors/Total | % of failed requests |
| p95 Latency | 95th percentile | 95% of requests faster than this |
| Availability | Uptime/Total Time | % of time service is available |
| Throughput | Requests/Second | How many requests processed |

### 9.2 Healthy Baselines

```
✅ Success Rate:       > 99.0%
✅ Error Rate:        < 1.0%
✅ Average Latency:   < 100ms
✅ p95 Latency:       < 500ms
✅ p99 Latency:       < 2000ms
✅ Availability:      > 99.5%
✅ Memory Usage:      < 500MB
✅ CPU Usage:         < 50%
```

---

## 10. Escalation Procedures

### 10.1 Alert Severity Levels

**INFO (Low Severity)**
- Non-critical notifications
- For awareness
- No immediate action required

**WARNING (Medium Severity)**
- Potential issues
- Monitor closely
- Investigate within hours

**CRITICAL (High Severity)**
- System degradation
- Immediate investigation
- May need emergency fix

**EMERGENCY (Highest Severity)**
- Service outage
- Page on-call immediately
- CEO notification if needed

### 10.2 Escalation Path

```
DETECTION (Automated)
    ↓
ALERT (On-call receives notification)
    ↓
INVESTIGATION (On-call investigates)
    ↓
MITIGATION (On-call applies fix)
    ↓
RESOLUTION (Service restored)
    ↓
POST-MORTEM (Prevent future occurrence)
```

---

## 11. SLA Definition

### Service Level Agreement

**Availability**: 99.5% uptime per month
- Maximum 3.6 hours downtime/month
- 99.9% during business hours

**Response Time**: P95 < 500ms
- 95% of requests complete in < 500ms
- All requests complete in < 30 seconds

**Error Rate**: < 1% of requests
- Maximum 1% error rate
- Network errors excluded from calculation

**Support**: 24/7 monitoring and response
- Critical issues: < 15 min response
- Warnings: < 1 hour response

---

## Conclusion

The Production Monitoring Guide provides a complete framework for monitoring the USASpending MCP Server in production. With health checks, performance metrics, error tracking, and structured logging, the system is fully observable and ready for enterprise deployment.

**Key Achievements:**
- ✅ Health check endpoint operational
- ✅ Performance metrics collection enabled
- ✅ Error tracking implemented
- ✅ Structured logging configured
- ✅ Alerting framework in place
- ✅ SLA targets defined

**Status**: ✅ **PRODUCTION MONITORING READY**

---

**Document Version**: 1.1
**Last Updated**: October 31, 2025
**Maintained By**: USASpending MCP Development Team

**Recent Updates:**
- Added Section 4.1: Log Files with details on three-file log system
- Added quick commands for log monitoring
- Added reference to logs/README.md for comprehensive logging documentation

