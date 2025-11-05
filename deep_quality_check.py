#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import re
import glob
import json
from collections import defaultdict

def detect_actual_country_from_content(name, description, country):
    """Detect the actual country/cuisine from recipe content"""

    # Mexican indicators
    mexican_terms = ['mexican', 'mexicana', 'mexicano', 'chile serrano', 'jalapeño',
                     'taco', 'burrito', 'enchilada', 'guacamole', 'salsa verde']

    # Italian indicators
    italian_terms = ['italian', 'italiano', 'italiana', 'ricetta', 'pasta',
                     'risotto', 'parmigiano', 'mozzarella', 'al dente']

    # French indicators
    french_terms = ['french', 'français', 'française', 'recette', 'c. à soupe',
                    'préparation', 'cuisson']

    # Irish indicators
    irish_terms = ['irish', 'irlandés', 'irlandesa', 'irlanda', 'guinness',
                   'st patrick', 'san patricio']

    # Turkish indicators
    turkish_terms = ['turkish', 'türk', 'turco', 'kebab', 'döner', 'baklava',
                     'börek', 'köfte', 'pide']

    text = (name + ' ' + description).lower()

    issues = []

    # Check for Mexican but marked as Spain
    if any(term in text for term in mexican_terms) and country == 'Spain':
        issues.append({
            'type': 'country_mismatch',
            'detected': 'Mexico',
            'current': country,
            'reason': 'Mexican cuisine indicators found'
        })

    # Check for Irish but marked as Spain
    if any(term in text for term in irish_terms) and country == 'Spain':
        issues.append({
            'type': 'country_mismatch',
            'detected': 'Ireland',
            'current': country,
            'reason': 'Irish cuisine indicators found'
        })

    # Check for Italian recipe in Italy - this is OK, but check language
    if country == 'Italy' and not any(term in text for term in italian_terms):
        # Italian country but no Italian terms?
        issues.append({
            'type': 'language_warning',
            'detected': 'Non-Italian language',
            'current': country,
            'reason': 'Italian country but description not in Italian'
        })

    # Check for French recipe in France
    if country == 'France' and not any(term in text for term in french_terms):
        issues.append({
            'type': 'language_warning',
            'detected': 'Non-French language',
            'current': country,
            'reason': 'French country but description not in French'
        })

    return issues

def detect_encoding_issues(text):
    """Detect character encoding problems"""
    issues = []

    # Common encoding issues
    patterns = {
        r'\?[a-z]': 'Question mark likely encoding error',
        r'[a-z]\?[a-z]': 'Mid-word question mark (encoding)',
        r'\\u[0-9a-f]{4}': 'Unicode escape sequence not decoded',
        r'\\x[0-9a-f]{2}': 'Hex escape sequence not decoded',
        r'&[a-z]+;': 'HTML entity not decoded'
    }

    for pattern, description in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            issues.append({
                'type': 'encoding',
                'pattern': pattern,
                'matches': matches[:3],  # First 3 examples
                'description': description
            })

    return issues

def detect_merged_words(text):
    """Detect merged words like 'lasrecetas' or 'deChamp'"""
    issues = []

    # Patterns for merged words
    patterns = [
        (r'\b[a-z]+[A-Z][a-z]+', 'CamelCase in middle of text'),
        (r'\b(la|el|de|un|una)[a-z]{3,}\b', 'Article merged with word'),
    ]

    for pattern, description in patterns:
        matches = re.findall(pattern, text)
        if matches:
            issues.append({
                'type': 'merged_words',
                'pattern': pattern,
                'matches': list(set(matches))[:5],
                'description': description
            })

    return issues

def deep_quality_check(csv_file):
    """Perform deep quality check on CSV file"""
    issues_by_recipe = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for recipe in reader:
            recipe_issues = {
                'id': recipe['id'],
                'name': recipe['name'],
                'country': recipe['country'],
                'issues': []
            }

            # Check country-language mismatch
            country_issues = detect_actual_country_from_content(
                recipe['name'],
                recipe['description'],
                recipe['country']
            )
            recipe_issues['issues'].extend(country_issues)

            # Check encoding in description
            desc_encoding = detect_encoding_issues(recipe['description'])
            recipe_issues['issues'].extend(desc_encoding)

            # Check encoding in instructions
            try:
                instructions = json.loads(recipe['instructions'])
                for inst in instructions:
                    inst_encoding = detect_encoding_issues(inst)
                    recipe_issues['issues'].extend(inst_encoding)
            except:
                pass

            # Check merged words
            merged = detect_merged_words(recipe['description'])
            recipe_issues['issues'].extend(merged)

            # Only keep recipes with issues
            if recipe_issues['issues']:
                issues_by_recipe.append(recipe_issues)

    return issues_by_recipe

def main():
    print("DEEP QUALITY ANALYSIS - Checking for REAL data issues")
    print("="*80)
    print("Checking:")
    print("  1. Country-cuisine mismatches")
    print("  2. Character encoding errors")
    print("  3. Merged words")
    print("  4. Language inconsistencies")
    print("="*80)

    all_issues = defaultdict(list)
    total_recipes_with_issues = 0

    csv_files = sorted(glob.glob('batch_*.csv'))[:5]  # Test first 5 files

    for csv_file in csv_files:
        print(f"\nAnalyzing {csv_file}...")
        issues = deep_quality_check(csv_file)

        for recipe_issues in issues:
            for issue in recipe_issues['issues']:
                issue_key = issue['type']
                all_issues[issue_key].append({
                    'file': csv_file,
                    'recipe': recipe_issues['name'],
                    'country': recipe_issues['country'],
                    'detail': issue
                })

        total_recipes_with_issues += len(issues)
        print(f"  Found {len(issues)} recipes with issues")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY OF REAL ISSUES")
    print("="*80)
    print(f"Total recipes with issues: {total_recipes_with_issues}")
    print(f"\nIssues by type:")

    for issue_type, issues_list in sorted(all_issues.items()):
        print(f"\n{issue_type.upper()}: {len(issues_list)} occurrences")

        # Show examples
        print("  Examples:")
        for issue in issues_list[:3]:
            print(f"    - {issue['recipe']} (Country: {issue['country']})")
            if 'reason' in issue['detail']:
                print(f"      Reason: {issue['detail']['reason']}")
            if 'detected' in issue['detail']:
                print(f"      Detected: {issue['detail']['detected']}")
            if 'matches' in issue['detail']:
                print(f"      Matches: {issue['detail']['matches']}")

    # Output JSON for further processing
    with open('quality_issues.json', 'w', encoding='utf-8') as f:
        json.dump(dict(all_issues), f, indent=2, ensure_ascii=False)

    print(f"\nDetailed issues saved to: quality_issues.json")

if __name__ == '__main__':
    main()
