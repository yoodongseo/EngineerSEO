import re
import ast

def parse_fan_status(output):
    
    result = []
    total_item = ""
    critical = output.get("fan").get("CRITICAL")
    data = output.get("fan")
    print(f"critical: {critical}")  
    is_pass = "1"
    for key, value in data.items():
        if isinstance(value, str):
            total_item += f'"{key}": "{value}"' + '\n'
            fan_value = int(value)
        else:
            total_item += f'"{key}": {value}' + '\n'
            fan_value = value
        
        
        print(f"fan_value: {fan_value}")
        
        if key != "CRITICAL":            
            if fan_value<= critical:
                is_pass = "0"    
    
    result.append({
                    "total_item": total_item,
                    "is_pass": is_pass,                    
                })
    
    return result

# Test
output = """
{
    "fan": { "FAN1": "5700", "FAN2": "6000", "FAN3": "5600", "FAN4": "6000", "FAN5": "5500", "FAN6": "6000", "CRITICAL": 2000 }
}
"""

output_dict = ast.literal_eval(output)

# # Parse the output and get usage percentages
info = parse_fan_status(output_dict)

# # Check if any pool usage exceeds 70%
for item in info:         
    print(f"total_item: {item.get('total_item')}")
    print(f"is_pass: {item.get('is_pass')}")
        
    
