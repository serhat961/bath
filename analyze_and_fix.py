#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import re
import html
import glob
import os
from typing import List, Dict, Tuple

def clean_description(description: str) -> Tuple[str, List[str]]:
    """Clean description field and return cleaned text + list of issues found"""
    if not description:
        return description, []

    issues = []
    original = description

    # Remove HTML tags
    if '<' in description and '>' in description:
        issues.append("HTML tags removed")
        description = re.sub(r'<[^>]+>', '', description)

    # Decode HTML entities
    decoded = html.unescape(description)
    if decoded != description:
        issues.append("HTML entities decoded")
        description = decoded

    # Remove price/calorie info (e.g., "Para100.2€/pers.368kcal/100g")
    pattern = r'Para\d+\.?\d*€/pers\.\d+kcal/100g'
    if re.search(pattern, description):
        issues.append("Price/calorie info removed")
        description = re.sub(pattern, '', description)

    # Remove rating info (e.g., "4.2/5870votos")
    pattern = r'\d+\.?\d*/\d+\s*votos?'
    if re.search(pattern, description):
        issues.append("Rating info removed")
        description = re.sub(pattern, '', description)

    # Remove date info (e.g., "Última revisión: 23 mayo 2025")
    pattern = r'Última revisión:\s*\d+\s+\w+\s+\d{4}'
    if re.search(pattern, description):
        issues.append("Date info removed")
        description = re.sub(pattern, '', description)

    # Remove category/tags sections
    pattern = r'Categorías:[^"]*'
    if re.search(pattern, description):
        issues.append("Category info removed")
        description = re.sub(pattern, '', description)

    pattern = r'Etiquetas:[^"]*'
    if re.search(pattern, description):
        issues.append("Tags info removed")
        description = re.sub(pattern, '', description)

    # Remove time tracking info
    pattern = r'\d+\s*min\.\s*(cocinando|para hacer|para redactar|para organizar)[^.]*\.'
    if re.search(pattern, description):
        issues.append("Time tracking info removed")
        description = re.sub(pattern, '', description)

    # Remove emoji and extra text about publishing process
    pattern = r'😊[^"]*'
    if re.search(pattern, description):
        issues.append("Publishing process info removed")
        description = re.sub(pattern, '', description)

    # Fix common character encoding issues
    replacements = {
        'mezz?oretta': 'mezz\'oretta',
        'finch\\u00e8': 'finché',
        '\\u00bd': '½',
        '\\u00e0': 'à',
        '\\u00e8': 'è',
        '\\u00e9': 'é',
        '\\u00ed': 'í',
        '\\u00f3': 'ó',
    }

    for wrong, right in replacements.items():
        if wrong in description:
            issues.append(f"Fixed encoding: {wrong} -> {right}")
            description = description.replace(wrong, right)

    # Clean up multiple spaces, newlines
    description = re.sub(r'\s+', ' ', description)
    description = description.strip()

    # Remove leading/trailing punctuation issues
    description = re.sub(r'^\s*[,;.]\s*', '', description)
    description = re.sub(r'\s*[,;.]\s*$', '', description)

    if description != original and not issues:
        issues.append("General cleanup")

    return description, issues

def clean_instructions(instructions: str) -> Tuple[str, List[str]]:
    """Clean instructions field"""
    if not instructions:
        return instructions, []

    issues = []
    original = instructions

    # Try to parse as list and clean each item
    try:
        # Instructions is often a JSON array string
        import json

        # First, try to extract the list part
        if instructions.startswith('[') and instructions.endswith(']'):
            items = json.loads(instructions)
            cleaned_items = []

            for item in items:
                # Skip obvious web artifacts
                if isinstance(item, str):
                    # Skip items that are clearly metadata
                    if any(x in item for x in ['Para', '€/pers', 'kcal/100g', 'votos', 'Categorías:',
                                                'Etiquetas:', 'Última revisión:', 'min.cocinando',
                                                'Carmen Tía Alia', '😊']):
                        issues.append(f"Removed metadata item: {item[:50]}...")
                        continue

                    # Remove HTML
                    cleaned_item = re.sub(r'<[^>]+>', '', item)
                    cleaned_item = html.unescape(cleaned_item)

                    # Clean whitespace
                    cleaned_item = re.sub(r'\s+', ' ', cleaned_item).strip()

                    if cleaned_item and len(cleaned_item) > 10:  # Keep substantial instructions
                        cleaned_items.append(cleaned_item)

            if len(cleaned_items) < len(items):
                issues.append(f"Removed {len(items) - len(cleaned_items)} metadata/invalid instructions")

            instructions = json.dumps(cleaned_items, ensure_ascii=False)
    except:
        # If not parseable as JSON, do basic cleaning
        issues.append("Could not parse as JSON, did basic cleaning")
        instructions = re.sub(r'<[^>]+>', '', instructions)
        instructions = html.unescape(instructions)

    return instructions, issues

def clean_ingredients(ingredients: str) -> Tuple[str, List[str]]:
    """Clean ingredients field"""
    if not ingredients:
        return ingredients, []

    issues = []
    original = ingredients

    try:
        import json

        if ingredients.startswith('[') and ingredients.endswith(']'):
            items = json.loads(ingredients)
            cleaned_items = []

            for item in items:
                if isinstance(item, str):
                    # Skip author names and other metadata
                    if any(x in item for x in ['Carmen Tía Alia', 'Preparación', 'Si tenéis',
                                                'Categorías', 'El calabacín']):
                        issues.append(f"Removed metadata from ingredients: {item[:50]}...")
                        continue

                    # Clean HTML
                    cleaned_item = re.sub(r'<[^>]+>', '', item)
                    cleaned_item = html.unescape(cleaned_item)
                    cleaned_item = re.sub(r'\s+', ' ', cleaned_item).strip()

                    if cleaned_item:
                        cleaned_items.append(cleaned_item)

            if len(cleaned_items) < len(items):
                issues.append(f"Removed {len(items) - len(cleaned_items)} invalid ingredients")

            ingredients = json.dumps(cleaned_items, ensure_ascii=False)
    except:
        issues.append("Could not parse ingredients as JSON, did basic cleaning")
        ingredients = re.sub(r'<[^>]+>', '', ingredients)
        ingredients = html.unescape(ingredients)

    return ingredients, issues

def analyze_and_fix_csv(input_file: str, output_file: str) -> Dict:
    """Analyze and fix a single CSV file"""
    stats = {
        'total_recipes': 0,
        'description_issues': 0,
        'instructions_issues': 0,
        'ingredients_issues': 0,
        'issues_by_type': {}
    }

    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames

            rows = []
            for row in reader:
                stats['total_recipes'] += 1

                # Clean description
                if 'description' in row:
                    cleaned_desc, desc_issues = clean_description(row['description'])
                    if desc_issues:
                        stats['description_issues'] += 1
                        for issue in desc_issues:
                            stats['issues_by_type'][issue] = stats['issues_by_type'].get(issue, 0) + 1
                    row['description'] = cleaned_desc

                # Clean instructions
                if 'instructions' in row:
                    cleaned_inst, inst_issues = clean_instructions(row['instructions'])
                    if inst_issues:
                        stats['instructions_issues'] += 1
                        for issue in inst_issues:
                            stats['issues_by_type'][issue] = stats['issues_by_type'].get(issue, 0) + 1
                    row['instructions'] = cleaned_inst

                # Clean ingredients
                if 'ingredients' in row:
                    cleaned_ingr, ingr_issues = clean_ingredients(row['ingredients'])
                    if ingr_issues:
                        stats['ingredients_issues'] += 1
                        for issue in ingr_issues:
                            stats['issues_by_type'][issue] = stats['issues_by_type'].get(issue, 0) + 1
                    row['ingredients'] = cleaned_ingr

                rows.append(row)

        # Write cleaned data
        with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return stats

    except Exception as e:
        print(f"Error processing {input_file}: {str(e)}")
        return None

def main():
    # Find all CSV files
    csv_files = sorted(glob.glob('batch_*.csv'))

    print(f"Found {len(csv_files)} CSV files to process")
    print("=" * 80)

    total_stats = {
        'total_files': len(csv_files),
        'total_recipes': 0,
        'total_description_issues': 0,
        'total_instructions_issues': 0,
        'total_ingredients_issues': 0,
        'issues_by_type': {}
    }

    # Create output directory
    output_dir = 'cleaned'
    os.makedirs(output_dir, exist_ok=True)

    for i, csv_file in enumerate(csv_files, 1):
        output_file = os.path.join(output_dir, csv_file)

        print(f"[{i}/{len(csv_files)}] Processing {csv_file}...", end=' ')

        stats = analyze_and_fix_csv(csv_file, output_file)

        if stats:
            total_stats['total_recipes'] += stats['total_recipes']
            total_stats['total_description_issues'] += stats['description_issues']
            total_stats['total_instructions_issues'] += stats['instructions_issues']
            total_stats['total_ingredients_issues'] += stats['ingredients_issues']

            for issue_type, count in stats['issues_by_type'].items():
                total_stats['issues_by_type'][issue_type] = \
                    total_stats['issues_by_type'].get(issue_type, 0) + count

            print(f"✓ ({stats['total_recipes']} recipes, {stats['description_issues']} desc issues)")
        else:
            print("✗ FAILED")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {total_stats['total_files']}")
    print(f"Total recipes: {total_stats['total_recipes']}")
    print(f"Recipes with description issues: {total_stats['total_description_issues']}")
    print(f"Recipes with instructions issues: {total_stats['total_instructions_issues']}")
    print(f"Recipes with ingredients issues: {total_stats['total_ingredients_issues']}")
    print("\nIssues by type:")
    for issue_type, count in sorted(total_stats['issues_by_type'].items(), key=lambda x: -x[1]):
        print(f"  - {issue_type}: {count}")

    print("\n" + "=" * 80)
    print(f"Cleaned files saved to: {output_dir}/")
    print("=" * 80)

if __name__ == '__main__':
    main()
