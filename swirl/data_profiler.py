'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import logging
logger = logging.getLogger(__name__)

from typing import List, Dict, Any
import statistics
from datetime import datetime
from dateutil import parser

def is_url(s: str) -> bool:
    return s.startswith('http://') or s.startswith('https://')

def can_be_unix_timestamp(value):
    try:
        if isinstance(value, str) and not value.isdigit():
            return False
        datetime.fromtimestamp(float(value))
        return True
    except (ValueError, OverflowError, TypeError):
        return False

def parse_date(value):
    try:
        return parser.parse(str(value))
    except (ValueError, TypeError):
        return None

def calculate_statistics(values):
    if all(isinstance(v, (int, float)) for v in values):
        return {
            "Median": statistics.median(values),
            "Max": max(values),
            "Population %": 100.0
        }
    elif all(isinstance(v, str) for v in values):
        lengths = [len(v) for v in values]
        return {
            "Median": statistics.median(lengths),
            "Max": max(lengths),
            "Population %": 100.0
        }
    return {}

def profile_data(data: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    aggregated_data = {'str': {}, 'int': {}, 'float': {}, 'date': {}, 'url': {}}

    for entry in data:
        for key, value in entry.items():
            if isinstance(value, dict):
                continue

            if "date" in key.lower():
                parsed_date = parse_date(value)
                if parsed_date:
                    aggregated_data['date'].setdefault(key, []).append(parsed_date)
                elif can_be_unix_timestamp(value):
                    datetime_str = datetime.fromtimestamp(float(value)).isoformat()
                    aggregated_data['date'].setdefault(key, []).append(datetime_str)
                else:
                    aggregated_data['str'].setdefault(key, []).append(value)
            elif isinstance(value, str):
                if is_url(value):
                    aggregated_data['url'].setdefault(key, []).append(value)
                else:
                    aggregated_data['str'].setdefault(key, []).append(value)
            elif isinstance(value, int):
                aggregated_data['int'].setdefault(key, []).append(value)
            elif isinstance(value, float):
                aggregated_data['float'].setdefault(key, []).append(value)

    result = {}
    for data_type, fields in aggregated_data.items():
        result[data_type] = {}
        for field, values in fields.items():
            if data_type == 'date':
                result[data_type][field] = {"Population %": (len(values) / len(data)) * 100}
            else:
                result[data_type][field] = calculate_statistics(values)

    return result

def find_longest_most_populated_field(profile_type):
    max_length = -1
    max_population = -1
    longest_most_populated_field = None

    for field, stats in profile_type.items():
        if isinstance(stats, dict):
            length = stats.get("Max", 0)
            population = stats.get("Population %", 0)

            if length > max_length or (length == max_length and population > max_population):
                max_length = length
                max_population = population
                longest_most_populated_field = field

    return longest_most_populated_field

def find_closest_median_most_populated_field(profile, target_median):
    str_fields = profile

    best_score = float('inf')
    best_field = None

    for field, stats in str_fields.items():
        median_length = stats.get("Median", 0)
        population = stats.get("Population %", 0)

        median_diff = abs(median_length - target_median)

        score = median_diff + (100 - population)

        if score < best_score:
            best_score = score
            best_field = field

    return best_field

def list_by_population_desc(profile_type):
    population_list = [(field, stats.get("Population %", 0)) for field, stats in profile_type.items()]
    sorted_population_list = sorted(population_list, key=lambda x: x[1]) #, reverse=True)
    sorted_fields = [field for field, _ in sorted_population_list]
    return sorted_fields

def find_most_populated_field(profile):
    max_population = -1
    most_populated_field = None
    most_populated_type = None

    for data_type, fields in profile.items():
        for field, stats in fields.items():
            population = stats.get("Population %", 0)

            if population > max_population:
                max_population = population
                most_populated_field = field
                most_populated_type = data_type

    return most_populated_type, most_populated_field

def filter_elements_case_insensitive(a, b):
    prefixes = set(key[0].lower() for key in b if key)
    suffixes = set(key[-1].lower() for key in b if key)
    result = [element for element in a if element and (element[0].lower() in prefixes or element[-1].lower() in suffixes)]
    return result
