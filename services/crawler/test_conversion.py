#!/usr/bin/env python3
"""Test script to verify HTML-to-Markdown conversion improvements."""

from main import clean_content

# Test 1: Table conversion
print("=" * 60)
print("TEST 1: TABLE CONVERSION")
print("=" * 60)
html_table = '''
<table>
<thead>
<tr><th>Stt</th><th>Họ và tên</th><th>Đơn vị công tác</th></tr>
</thead>
<tbody>
<tr><td>1</td><td>GS.TS. Nguyễn Hữu Đức</td><td>Chủ tịch Hội đồng Khoa học và Đào tạo</td></tr>
<tr><td>2</td><td>GS.TSKH Nguyễn Đình Đức</td><td>Khoa Công nghệ Xây dựng – Giao thông</td></tr>
</tbody>
</table>
'''
print(clean_content(html_table))
print()

# Test 2: Heading conversion
print("=" * 60)
print("TEST 2: HEADING CONVERSION")
print("=" * 60)
html_heading = '<h2>I. Danh sách Giáo sư</h2>'
print(clean_content(html_heading))
print()

# Test 3: Nested list conversion
print("=" * 60)
print("TEST 3: NESTED LIST CONVERSION")
print("=" * 60)
html_list = '''
<ul>
    <li>335 cán bộ cơ hữu
        <ul>
            <li>269 giảng viên, trợ giảng, nghiên cứu viên</li>
            <li>61 cán bộ hành chính, kỹ thuật</li>
        </ul>
    </li>
    <li>37 cán bộ thỉnh giảng</li>
</ul>
'''
print(clean_content(html_list))
print()

# Test 4: Mixed content (like the staff page)
print("=" * 60)
print("TEST 4: MIXED CONTENT (STAFF PAGE SIMULATION)")
print("=" * 60)
html_mixed = '''
<h1>Đội ngũ cán bộ</h1>
<p>Trường Đại học Công nghệ hiện có 372 cán bộ, bao gồm:</p>
<ul>
    <li>335 cán bộ cơ hữu
        <ul>
            <li>269 giảng viên, trợ giảng, nghiên cứu viên</li>
            <li>61 cán bộ hành chính, kỹ thuật</li>
        </ul>
    </li>
    <li>37 cán bộ thỉnh giảng</li>
</ul>
<h2>I. Danh sách Giáo sư</h2>
<table>
<thead>
<tr><th>Stt</th><th>Họ và tên</th><th>Đơn vị công tác</th></tr>
</thead>
<tbody>
<tr><td>1</td><td>GS.TS. Nguyễn Hữu Đức</td><td>Chủ tịch Hội đồng Khoa học và Đào tạo</td></tr>
<tr><td>2</td><td>GS.TSKH Nguyễn Đình Đức</td><td>Khoa Công nghệ Xây dựng – Giao thông</td></tr>
</tbody>
</table>
'''
print(clean_content(html_mixed))
print()

print("=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)
