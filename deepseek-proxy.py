#!/usr/bin/env python3
"""
DeepSeek proxy for Codex CLI.

Translates OpenAI Responses API (/v1/responses) streaming format
into DeepSeek Chat Completions API calls, then converts the response
back into Responses API SSE events that Codex CLI can parse.

Root cause of "stream disconnected before completion":
  Codex CLI expects Responses API SSE events (response.output_text.delta, etc.)
  but the old proxy just piped through Chat Completions chunks raw.
"""
from flask import Flask, request, Response, stream_with_context
import requests
import json
import os
import logging
import uuid
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
if not DEEPSEEK_API_KEY:
    logger.error("请设置 DEEPSEEK_API_KEY 环境变量")
    exit(1)

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
UPSTREAM_TIMEOUT = int(os.getenv('UPSTREAM_TIMEOUT', '120'))


ROLE_MAP = {
    'developer': 'system',  # OpenAI-specific → nearest DeepSeek equivalent
    'latest_reminder': 'system',
}


def extract_messages(data):
    """Convert Codex Responses API request into Chat Completions messages."""
    messages = []

    if 'instructions' in data:
        messages.append({"role": "system", "content": data['instructions']})

    input_data = data.get('input', '')
    if isinstance(input_data, str):
        messages.append({"role": "user", "content": input_data})
    elif isinstance(input_data, list):
        for item in input_data:
            if not isinstance(item, dict):
                continue
            role = item.get('role', 'user')
            role = ROLE_MAP.get(role, role)  # remap unsupported roles
            content = item.get('content', '')
            # content can be a list of content parts
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        text_parts.append(part.get('text', part.get('input_text', '')))
                content = ''.join(text_parts)
            messages.append({"role": role, "content": content})

    return messages


def sse(event_type, data):
    """Format a single SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.route('/v1/responses', methods=['POST'])
def proxy():
    logger.info("=" * 50)

    try:
        data = request.json or {}
        messages = extract_messages(data)

        if not messages:
            return Response(json.dumps({"error": "No messages extracted"}), status=400,
                            content_type='application/json')

        response_id = f"resp_{uuid.uuid4().hex[:24]}"
        msg_id = f"msg_{uuid.uuid4().hex[:24]}"
        created_at = int(time.time())
        model = data.get('model', 'deepseek-chat')
        do_stream = data.get('stream', True)

        logger.info(f"Model={model} stream={do_stream} msgs={len(messages)}")

        if do_stream:
            return _stream_response(messages, response_id, msg_id, created_at, model)
        else:
            return _sync_response(messages, response_id, msg_id, created_at, model)

    except Exception as e:
        logger.error(f"Proxy error: {e}", exc_info=True)
        return Response(json.dumps({"error": str(e)}), status=500,
                        content_type='application/json')


def _stream_response(messages, response_id, msg_id, created_at, model):
    """Stream Responses API SSE events translated from DeepSeek chunks."""

    try:
        ds_resp = requests.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": messages, "stream": True},
            stream=True,
            timeout=UPSTREAM_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        logger.error("DeepSeek request timed out")
        return Response(json.dumps({"error": "upstream timeout"}), status=504,
                        content_type='application/json')
    except requests.exceptions.RequestException as e:
        logger.error(f"DeepSeek request failed: {e}")
        return Response(json.dumps({"error": str(e)}), status=502,
                        content_type='application/json')

    if ds_resp.status_code != 200:
        body = ds_resp.text
        logger.error(f"DeepSeek error {ds_resp.status_code}: {body}")
        return Response(body, status=ds_resp.status_code,
                        content_type='application/json')

    def generate():
        full_text = []

        # --- Responses API preamble events ---
        yield sse("response.created", {
            "type": "response.created",
            "response": {
                "id": response_id,
                "object": "response",
                "created_at": created_at,
                "status": "in_progress",
                "model": model,
                "output": [],
            },
        })

        yield sse("response.output_item.added", {
            "type": "response.output_item.added",
            "response_id": response_id,
            "output_index": 0,
            "item": {
                "id": msg_id,
                "type": "message",
                "status": "in_progress",
                "role": "assistant",
                "content": [],
            },
        })

        yield sse("response.content_part.added", {
            "type": "response.content_part.added",
            "item_id": msg_id,
            "output_index": 0,
            "content_index": 0,
            "part": {"type": "output_text", "text": ""},
        })

        # --- Translate DeepSeek Chat Completions chunks → delta events ---
        try:
            for raw_line in ds_resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode('utf-8') if isinstance(raw_line, bytes) else raw_line
                if line.startswith('data: '):
                    line = line[6:]
                if line == '[DONE]':
                    break
                try:
                    chunk = json.loads(line)
                    delta_text = (chunk.get('choices', [{}])[0]
                                       .get('delta', {})
                                       .get('content', ''))
                    if delta_text:
                        full_text.append(delta_text)
                        yield sse("response.output_text.delta", {
                            "type": "response.output_text.delta",
                            "item_id": msg_id,
                            "output_index": 0,
                            "content_index": 0,
                            "delta": delta_text,
                        })
                except (json.JSONDecodeError, IndexError, KeyError) as e:
                    logger.debug(f"Skipping unparseable chunk: {e}")
        except Exception as e:
            logger.error(f"Error reading DeepSeek stream: {e}", exc_info=True)

        final_text = ''.join(full_text)

        # --- Responses API closing events ---
        yield sse("response.output_text.done", {
            "type": "response.output_text.done",
            "item_id": msg_id,
            "output_index": 0,
            "content_index": 0,
            "text": final_text,
        })

        yield sse("response.output_item.done", {
            "type": "response.output_item.done",
            "response_id": response_id,
            "output_index": 0,
            "item": {
                "id": msg_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [{"type": "output_text", "text": final_text}],
            },
        })

        yield sse("response.completed", {
            "type": "response.completed",
            "response": {
                "id": response_id,
                "object": "response",
                "created_at": created_at,
                "status": "completed",
                "model": model,
                "output": [{
                    "id": msg_id,
                    "type": "message",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": final_text}],
                }],
            },
        })

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # disable nginx buffering if behind nginx
        },
    )


def _sync_response(messages, response_id, msg_id, created_at, model):
    """Non-streaming fallback: call DeepSeek and return a full Responses API object."""
    try:
        ds_resp = requests.post(
            DEEPSEEK_URL,
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": messages, "stream": False},
            timeout=UPSTREAM_TIMEOUT,
        )
    except requests.exceptions.Timeout:
        return Response(json.dumps({"error": "upstream timeout"}), status=504,
                        content_type='application/json')
    except requests.exceptions.RequestException as e:
        return Response(json.dumps({"error": str(e)}), status=502,
                        content_type='application/json')

    if ds_resp.status_code != 200:
        return Response(ds_resp.text, status=ds_resp.status_code,
                        content_type='application/json')

    text = (ds_resp.json()
                   .get('choices', [{}])[0]
                   .get('message', {})
                   .get('content', ''))

    body = {
        "id": response_id,
        "object": "response",
        "created_at": created_at,
        "status": "completed",
        "model": model,
        "output": [{
            "id": msg_id,
            "type": "message",
            "status": "completed",
            "role": "assistant",
            "content": [{"type": "output_text", "text": text}],
        }],
    }
    return Response(json.dumps(body), content_type='application/json')


@app.route('/health', methods=['GET'])
def health():
    return {"status": "ok"}


if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    print(f"DeepSeek proxy listening on http://localhost:{port}")
    # threaded=True is important for concurrent SSE streams
    # debug=False avoids Flask's reloader interfering with streaming
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
