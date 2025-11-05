#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import re
import glob
import json
import os

def fix_unicode_escapes(text):
    """Fix Unicode escape sequences"""
    if not text:
        return text

    # Common Unicode mappings
    unicode_map = {
        '\\u00e0': 'à', '\\u00e1': 'á', '\\u00e2': 'â', '\\u00e3': 'ã',
        '\\u00e8': 'è', '\\u00e9': 'é', '\\u00ea': 'ê',
        '\\u00ec': 'ì', '\\u00ed': 'í', '\\u00ee': 'î',
        '\\u00f2': 'ò', '\\u00f3': 'ó', '\\u00f4': 'ô', '\\u00f5': 'õ',
        '\\u00f9': 'ù', '\\u00fa': 'ú', '\\u00fb': 'û',
        '\\u00e7': 'ç',
        '\\u00f1': 'ñ',
        '\\u00b0': '°',
        '\\u00bd': '½',
        '\\u2019': "'",
        '\\u2018': "'",
        '\\u201c': '"',
        '\\u201d': '"',
    }

    for escape, char in unicode_map.items():
        text = text.replace(escape, char)

    return text

def fix_question_mark_encoding(text):
    """Fix question marks that are encoding errors"""
    if not text:
        return text

    # Common patterns: mezz?oretta → mezz'oretta, finch? → finché
    replacements = {
        "mezz?oretta": "mezz'oretta",
        "mezz?ora": "mezz'ora",
        "un?ora": "un'ora",
        "un po?": "un po'",
        "finch?": "finché",
        "perch?": "perché",
        "poich?": "poiché",
        "cos?": "così",
        "pi?": "più",
        "sar?": "sarà",
        "cio?": "cioè",
    }

    for wrong, right in replacements.items():
        text = text.replace(wrong, right)

    # Pattern: letter?letter → letter'letter (for Italian contractions)
    text = re.sub(r'([a-z])\?([a-z])', r"\1'\2", text)

    return text

def detect_country_from_recipe(name, description, ingredients_str):
    """More accurate country detection - ONLY for OBVIOUS cases"""
    # Only check name and description, NOT ingredients (too unreliable)
    text = (name + ' ' + description).lower()

    # Mexican cuisine indicators (be VERY specific - only clear terms)
    mexican_strong = ['mexicana', 'mexicano', 'mexican',
                      'fajitas', 'quesadilla', 'enchilada',
                      'tacos', 'guacamole', 'pico de gallo', 'flautas']

    # Irish indicators (VERY specific)
    irish_strong = ['guinness', 'st patrick', 'san patricio', 'patrick\'s day',
                    'irlandés', 'irlandesa', 'irlanda', 'ireland', 'irish']

    # Colombian indicators (VERY specific)
    colombian_strong = ['colombiana', 'colombiano', 'colombia',
                        'arepa', 'bandeja paisa']

    # ONLY change if the term appears in NAME or very start of description
    name_lower = name.lower()

    # Check name first (most reliable)
    if any(term in name_lower for term in mexican_strong):
        return 'Mexico'
    elif any(term in name_lower for term in irish_strong):
        return 'Ireland'
    elif any(term in name_lower for term in colombian_strong):
        return 'Colombia'

    # Check first 100 chars of description (intro usually mentions origin)
    desc_start = description[:100].lower()

    if any(term in desc_start for term in mexican_strong):
        return 'Mexico'
    elif any(term in desc_start for term in irish_strong):
        return 'Ireland'
    elif any(term in desc_start for term in colombian_strong):
        return 'Colombia'

    return None  # No change

def fix_csv_file(input_file, output_file):
    """Fix real quality issues in CSV file"""
    stats = {
        'total': 0,
        'country_fixed': 0,
        'encoding_fixed': 0,
    }

    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        rows = []

        for row in reader:
            stats['total'] += 1
            original_row = row.copy()

            # Fix encoding in description
            if row['description']:
                fixed_desc = fix_unicode_escapes(row['description'])
                fixed_desc = fix_question_mark_encoding(fixed_desc)
                if fixed_desc != row['description']:
                    stats['encoding_fixed'] += 1
                row['description'] = fixed_desc

            # Fix encoding in instructions
            if row['instructions']:
                try:
                    instructions = json.loads(row['instructions'])
                    if isinstance(instructions, list):
                        fixed_instructions = []
                        for inst in instructions:
                            if isinstance(inst, str):
                                fixed = fix_unicode_escapes(inst)
                                fixed = fix_question_mark_encoding(fixed)
                                fixed_instructions.append(fixed)
                            else:
                                # Complex instruction format (dict)
                                if isinstance(inst, dict) and 'instruction' in inst:
                                    inst['instruction'] = fix_unicode_escapes(inst['instruction'])
                                    inst['instruction'] = fix_question_mark_encoding(inst['instruction'])
                                fixed_instructions.append(inst)
                        row['instructions'] = json.dumps(fixed_instructions, ensure_ascii=False)
                except:
                    pass

            # Fix country mismatches (only clear cases)
            detected_country = detect_country_from_recipe(
                row['name'],
                row['description'],
                row['ingredients']
            )

            if detected_country and detected_country != row['country']:
                # Only fix if current is Spain and we detected something specific
                if row['country'] == 'Spain':
                    row['country'] = detected_country
                    stats['country_fixed'] += 1

            rows.append(row)

    # Write fixed data
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return stats

def main():
    csv_files = sorted(glob.glob('batch_*.csv'))

    print("FIXING REAL DATA QUALITY ISSUES")
    print("="*80)
    print(f"Found {len(csv_files)} CSV files to process")
    print("="*80)

    total_stats = {
        'total': 0,
        'country_fixed': 0,
        'encoding_fixed': 0,
    }

    # Create fixed output directory
    output_dir = 'fixed'
    os.makedirs(output_dir, exist_ok=True)

    for i, csv_file in enumerate(csv_files, 1):
        output_file = os.path.join(output_dir, csv_file)

        print(f"[{i}/{len(csv_files)}] Processing {csv_file}...", end=' ')

        stats = fix_csv_file(csv_file, output_file)

        total_stats['total'] += stats['total']
        total_stats['country_fixed'] += stats['country_fixed']
        total_stats['encoding_fixed'] += stats['encoding_fixed']

        print(f"✓ (Country: {stats['country_fixed']}, Encoding: {stats['encoding_fixed']})")

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total recipes processed: {total_stats['total']}")
    print(f"Country mismatches fixed: {total_stats['country_fixed']}")
    print(f"Recipes with encoding fixes: {total_stats['encoding_fixed']}")
    print(f"\nFixed files saved to: {output_dir}/")
    print("="*80)

if __name__ == '__main__':
    main()
