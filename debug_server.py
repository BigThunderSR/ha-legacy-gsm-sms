#!/usr/bin/env python3
"""
Debug HTTP Server - Captures and displays all incoming request details
Use this to analyze what your application is actually sending

Run: python3 debug_server.py
Then configure your app to send to: http://192.168.1.37:5555/sms
"""

from flask import Flask, request
import json
from datetime import datetime

app = Flask(__name__)

def log_request(endpoint):
    """Log all details of the incoming request"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print("\n" + "=" * 80)
    print(f"📥 REQUEST RECEIVED at {timestamp}")
    print("=" * 80)
    
    print(f"\n🎯 Endpoint: {request.method} {endpoint}")
    print(f"🌐 URL: {request.url}")
    print(f"🔗 Path: {request.path}")
    
    print(f"\n📋 Headers:")
    for header, value in request.headers.items():
        print(f"  {header}: {value}")
    
    print(f"\n📦 Content-Type: {request.content_type or 'NOT SET'}")
    
    # Try to get raw body
    try:
        raw_body = request.get_data(as_text=True)
        print(f"\n📄 Raw Body ({len(raw_body)} bytes):")
        print(f"  {repr(raw_body)}")
        print(f"  Actual: {raw_body}")
    except Exception as e:
        print(f"\n❌ Could not read raw body: {e}")
    
    # Try to parse as JSON
    print(f"\n🔍 Parsed Data:")
    try:
        json_data = request.get_json(silent=True)
        if json_data:
            print(f"  ✅ JSON: {json.dumps(json_data, indent=2)}")
        else:
            print(f"  ❌ Not valid JSON")
    except Exception as e:
        print(f"  ❌ JSON parse error: {e}")
    
    # Try to parse as form data
    if request.form:
        print(f"  ✅ Form Data:")
        for key, value in request.form.items():
            print(f"    {key} = {repr(value)}")
    else:
        print(f"  ❌ No form data detected")
    
    # Query parameters
    if request.args:
        print(f"\n🔗 Query Parameters:")
        for key, value in request.args.items():
            print(f"  {key} = {repr(value)}")
    else:
        print(f"\n  No query parameters")
    
    print("\n" + "=" * 80)
    print("✅ Analysis complete - check above for issues")
    print("=" * 80 + "\n")

@app.route('/sms', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def sms_endpoint():
    """Main SMS endpoint - logs everything and returns success"""
    log_request('/sms')
    
    return {
        "status": 200,
        "message": "Debug server received your request - check console output",
        "received_at": datetime.now().isoformat(),
        "method": request.method,
        "content_type": request.content_type,
        "body_length": len(request.get_data())
    }, 200

@app.route('/', methods=['GET', 'POST'])
def root():
    """Catch-all for root"""
    log_request('/')
    return {"message": "Debug server running - use /sms endpoint"}, 200

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
def catch_all(path):
    """Catch any other endpoint"""
    log_request(f'/{path}')
    return {"message": f"Debug server - wrong endpoint (use /sms)"}, 200

if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("🔍 DEBUG HTTP SERVER STARTED")
    print("=" * 80)
    print("\n📡 Listening on: http://0.0.0.0:5555")
    print("🎯 Configure your app to send to: http://192.168.1.37:5555/sms")
    print("\n💡 This server will log EVERYTHING it receives")
    print("   - All headers")
    print("   - Content-Type")
    print("   - Raw body")
    print("   - Parsed JSON (if applicable)")
    print("   - Form data (if applicable)")
    print("\n⏸️  Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=5555, debug=False)
