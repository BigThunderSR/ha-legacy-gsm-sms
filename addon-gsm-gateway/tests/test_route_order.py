"""
Test to verify Flask-RESTX route registration order
Ensures endpoints appear in the correct order in Swagger UI
"""
import pytest
import sys
import os

# Add parent directory to path to import run.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_route_definitions_exist():
    """Verify all SMS routes are properly defined in run.py"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'run.py'), 'r') as f:
        content = f.read()
    
    # Check all routes exist
    assert "@ns_sms.route('')" in content, "POST /sms route not found"
    assert "@ns_sms.route('/add/<path:sms_data>')" in content, "GET /sms/add/{sms_data} route not found"
    assert "@ns_sms.route('/<path:sms_data>')" in content, "GET /sms/{sms_data} route not found"
    assert "@ns_sms.route('/getsms')" in content, "GET /sms/getsms route not found"
    assert "@ns_sms.route('/deleteall')" in content, "DELETE /sms/deleteall route not found"
    assert "@ns_sms.route('/<int:id>')" in content, "GET/DELETE /sms/{id} route not found"


def test_route_order():
    """Verify routes are defined in the correct order for Swagger UI"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'run.py'), 'r') as f:
        lines = f.readlines()
    
    # Find line numbers for each route
    route_lines = {}
    for i, line in enumerate(lines, 1):
        if "@ns_sms.route('')" in line:
            route_lines['post_sms'] = i
        elif "@ns_sms.route('/<path:sms_data>')" in line:
            route_lines['get_sms_path'] = i
        elif "@ns_sms.route('/getsms')" in line:
            route_lines['get_sms_list'] = i
        elif "@ns_sms.route('/deleteall')" in line:
            route_lines['delete_all'] = i
        elif "@ns_sms.route('/<int:id>')" in line:
            route_lines['sms_by_id'] = i
    
    # Verify all routes found
    assert len(route_lines) == 5, f"Expected 5 routes, found {len(route_lines)}"
    
    # Verify order: POST /sms → GET /sms/{sms_data} → GET /getsms → DELETE /deleteall → /{id}
    assert route_lines['post_sms'] < route_lines['get_sms_path'], \
        "POST /sms should come before GET /sms/{sms_data}"
    assert route_lines['get_sms_path'] < route_lines['get_sms_list'], \
        "GET /sms/{sms_data} should come before GET /getsms"
    assert route_lines['get_sms_list'] < route_lines['delete_all'], \
        "GET /getsms should come before DELETE /deleteall"
    assert route_lines['delete_all'] < route_lines['sms_by_id'], \
        "DELETE /deleteall should come before /{id}"
    
    print(f"\n✅ Route order correct:")
    print(f"  1. POST /sms (line {route_lines['post_sms']})")
    print(f"  2. GET /sms/{{sms_data}} (line {route_lines['get_sms_path']})")
    print(f"  3. GET /sms/getsms (line {route_lines['get_sms_list']})")
    print(f"  4. DELETE /sms/deleteall (line {route_lines['delete_all']})")
    print(f"  5. GET/DELETE /sms/{{id}} (line {route_lines['sms_by_id']})")


def test_no_duplicate_classes():
    """Verify there are no duplicate class definitions"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'run.py'), 'r') as f:
        content = f.read()
    
    # Check for duplicate class definitions
    classes = ['SmsCollection', 'SmsGet', 'GetSms', 'DeleteAllSms', 'SmsItem']
    for cls in classes:
        count = content.count(f'class {cls}(Resource)')
        assert count == 1, f"Class {cls} defined {count} times (expected 1)"


def test_deduplication_cache_defined():
    """Verify deduplication cache is properly defined"""
    with open(os.path.join(os.path.dirname(__file__), '..', 'run.py'), 'r') as f:
        content = f.read()
    
    assert '_sms_dedup_cache = {}' in content, "Deduplication cache not initialized"
    assert '_sms_dedup_window = 15' in content, "Deduplication window not set"
    assert 'global _sms_dedup_cache' in content, "Cache not declared as global"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
