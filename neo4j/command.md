// Xóa toàn bộ nodes và relationships trong database
MATCH (n) DETACH DELETE n;

// Chỉ xóa các node có nhãn (Label) cụ thể
MATCH (n:Entity) DETACH DELETE n;

// Xem 50 node bất kỳ (để test)
MATCH (n) RETURN n LIMIT 50;

// Tìm các node có nhãn cụ thể (ví dụ: University)
MATCH (u:University) RETURN u LIMIT 10;

// Tìm node dựa trên thuộc tính cụ thể
MATCH (p:Person {name: 'Quyen'}) RETURN p;

// Xem toàn bộ một đồ thị nhỏ (Node A -> Relationship -> Node B)
MATCH (a)-[r]->(b) RETURN a, r, b LIMIT 50;

// Tìm tất cả những ai có quan hệ với một trường đại học cụ thể
MATCH (p:Person)-[r:STUDIES_AT]->(u:University {name: 'VNU'}) 
RETURN p, r, u;

// Tạo mới một liên kết giữa 2 node đã có sẵn
MATCH (p:Person {name: 'Quyen'}), (u:University {name: 'VNU'})
CREATE (p)-[:STUDIES_AT]->(u);

// Đếm tổng số lượng node đang có trong db
MATCH (n) RETURN count(n);

// Đếm số lượng node phân theo từng loại Nhãn (Label)
MATCH (n) 
RETURN labels(n)[0] AS Label, count(n) AS Count 
ORDER BY Count DESC;

// Đếm số lượng các loại Relationship
MATCH ()-[r]->() 
RETURN type(r) AS RelationshipType, count(r) AS Count
ORDER BY Count DESC;

// Xóa một thuộc tính (property) của node
MATCH (n:Person {name: 'Quyen'}) 
REMOVE n.age 
RETURN n;

// Xóa một node cụ thể (nhớ dùng DETACH để xóa luôn các quan hệ dính tới nó)
MATCH (n:Entity {id: '123'}) DETACH DELETE n;