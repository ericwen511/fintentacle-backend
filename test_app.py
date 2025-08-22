#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello():
    return {"message": "Hello from FinTentacle Backend!", "status": "working"}

@app.route('/health')
def health():
    return {"status": "healthy", "service": "fintentacle-backend"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

