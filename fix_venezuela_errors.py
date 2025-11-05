#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import glob

# Venezuela olması gereken tarifler (isimde Venezuela geçenler veya açıkça Venezuela tarifi olanlar)
VENEZUELA_RECIPES = [
    'Arepas de maíz dulce típicas de Venezuela',
    'Arepa reina pepiada tradicional de Venezuela',
    'Receta de Torta María Luisa',  # Venezuela dessert
    'Receta de Arepas vegetarianas',  # Mentions Venezuela in desc
    'Carne mechada venezolana',
    'Receta de Arepas de avena',
    'Arepas de Perico',
    'Receta de Caraotas venezolanas',
    'Receta de Arepas de maíz fritas',
    'Receta de Cachapas venezolanas',
    'Arepas rellenas de aguacate, pollo y mayonesa',
    'Arepas pelúas',
    'Agua de guanábana',  # Venezuela in desc
    'Receta de Arepas de yuca',
    'Receta de Empanadas de zanahoria con queso'  # Venezuela/Colombia shared but desc mentions Venezuela
]

def fix_venezuela_errors():
    """Fix Venezuela recipes incorrectly marked as Colombia"""

    print("DÜZELTME: Venezuela tarifleri Colombia'dan düzeltiliyor...")
    print("="*80)

    total_fixed = 0

    for batch_file in sorted(glob.glob('fixed/batch_*.csv')):
        rows = []
        changes_in_file = 0

        with open(batch_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            for row in reader:
                # Check if this recipe should be Venezuela
                if row['country'] == 'Colombia':
                    name = row['name']
                    desc = row['description'].lower()

                    # Exact match in our list
                    if any(venezuela_name in name for venezuela_name in VENEZUELA_RECIPES):
                        row['country'] = 'Venezuela'
                        changes_in_file += 1
                        print(f"  ✓ Fixed: {name[:60]}... → Venezuela")

                    # Or if Venezuela is explicitly mentioned in name
                    elif 'venezuela' in name.lower() or 'venezolan' in name.lower():
                        row['country'] = 'Venezuela'
                        changes_in_file += 1
                        print(f"  ✓ Fixed: {name[:60]}... → Venezuela")

                rows.append(row)

        # Write back if changes were made
        if changes_in_file > 0:
            with open(batch_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)

            total_fixed += changes_in_file
            print(f"  {batch_file}: {changes_in_file} fixes saved")

    print("="*80)
    print(f"TOTAL: {total_fixed} Venezuela recipes corrected")
    print("="*80)

if __name__ == '__main__':
    fix_venezuela_errors()
