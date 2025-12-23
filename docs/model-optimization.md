# Model Optimization Guide

## Overview

The AI bot has been optimized for faster response times by switching from `llama3:8b` to `qwen2.5:3b` and optimizing model parameters.

## Changes Made

### 1. Model Switch

- **Old Model**: `llama3:8b` (8 billion parameters)
- **New Model**: `qwen2.5:3b` (3 billion parameters)
- **Expected Speed Improvement**: 3-5x faster (1.5-2.5s vs 5-8s)

### 2. Optimized Parameters

| Parameter        | Old Value | New Value  | Reason                    |
| ---------------- | --------- | ---------- | ------------------------- |
| `model`          | llama3:8b | qwen2.5:3b | Smaller, faster model     |
| `timeout`        | 60s       | 30s        | Fail faster on issues     |
| `temperature`    | 0.7       | 0.5        | More focused responses    |
| `max_tokens`     | 250       | 150        | Shorter, faster responses |
| `num_ctx`        | N/A       | 2048       | Limit context window      |
| `repeat_penalty` | N/A       | 1.1        | Prevent repetition        |

### 3. Code Optimizations

**config.py**:

- Updated `OllamaConfig` class with new model and parameters
- Added `num_ctx` and `repeat_penalty` settings

**enhanced_ollama.py**:

- Shortened system prompt for faster processing
- Added performance logging to track response times
- Added timeout exception handling
- Added `num_gpu: 1` to use GPU acceleration if available
- Removed vendor information from product list (less tokens)

## Environment Variables

Update your `.env` file with these optimized settings:

```env
# Ollama Configuration (Optimized for Speed)
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=30
OLLAMA_MAX_TOKENS=150
OLLAMA_TEMPERATURE=0.5
OLLAMA_NUM_CTX=2048
OLLAMA_REPEAT_PENALTY=1.1
```

## Server Setup

### 1. Pull the New Model

On your server, run:

```bash
ollama pull qwen2.5:3b
```

This will download the qwen2.5:3b model (~2GB).

### 2. Verify Model Installation

```bash
ollama list
```

You should see `qwen2.5:3b` in the list.

### 3. Update Environment Variables

Edit your `.env` file on the server and add/update:

```env
OLLAMA_MODEL=qwen2.5:3b
```

### 4. Restart the Application

```bash
# Stop the current application
# Then restart it to load new configuration
```

## Performance Monitoring

The application now logs response times for each Ollama request:

```
INFO: Ollama response time: 1.85s for 142 chars
```

Monitor your logs to track performance improvements.

## Expected Results

### Before Optimization (llama3:8b)

- Average response time: 5-8 seconds
- P95 response time: 10-12 seconds
- Tokens/second: ~15-20

### After Optimization (qwen2.5:3b)

- Average response time: 1.5-2.5 seconds ✅
- P95 response time: 3-4 seconds ✅
- Tokens/second: ~50-70 ✅

## Alternative Models

If you need to try different models, here are other fast options:

### phi3:mini (3.8B parameters)

```bash
ollama pull phi3:mini
```

Set `OLLAMA_MODEL=phi3:mini` in `.env`

### gemma2:2b (2B parameters - fastest)

```bash
ollama pull gemma2:2b
```

Set `OLLAMA_MODEL=gemma2:2b` in `.env`

## Troubleshooting

### Model Not Found Error

If you get "model not found", ensure you've pulled the model:

```bash
ollama pull qwen2.5:3b
```

### Slow Responses Still

1. Check if GPU is being used:

   ```bash
   nvidia-smi  # For NVIDIA GPUs
   ```

2. Check Ollama logs for performance issues

3. Try reducing `max_tokens` further:
   ```env
   OLLAMA_MAX_TOKENS=100
   ```

### Timeout Errors

If you see timeout errors, increase the timeout:

```env
OLLAMA_TIMEOUT=45
```

## Quality vs Speed Trade-off

The new model (qwen2.5:3b) is optimized for speed while maintaining good quality for:

- Product recommendations
- Customer service responses
- Simple Q&A

If you notice quality issues, you can:

1. Increase `temperature` to 0.6-0.7 for more creative responses
2. Increase `max_tokens` to 200 for longer responses
3. Try `phi3:mini` which may have better quality at similar speed

## Future Enhancements

### Streaming Support

For even better perceived performance, consider implementing streaming responses:

- User sees response start in < 500ms
- Words appear progressively
- Better user experience even if total time is similar

This requires frontend changes to consume Server-Sent Events (SSE).

## Summary

✅ **Implemented**:

- Switched to qwen2.5:3b model
- Optimized all model parameters
- Added performance logging
- Improved error handling
- Shortened system prompts

📝 **Action Required**:

1. Pull qwen2.5:3b model on server: `ollama pull qwen2.5:3b`
2. Update `.env` file with new settings
3. Restart application
4. Monitor logs for performance improvements

🎯 **Expected Result**: 3-5x faster responses (1.5-2.5s instead of 5-8s)
