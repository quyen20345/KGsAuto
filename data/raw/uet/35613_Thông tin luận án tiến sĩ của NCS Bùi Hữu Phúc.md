# Thông tin luận án tiến sĩ của NCS Bùi Hữu Phúc

- ID: 35613
- Date: 2023-05-11T08:16:52
- URL: https://uet.edu.vn/thong-tin-luan-tien-si-cua-ncs-bui-huu-phuc-2/
- Categories: Đào tạo sau Đại học
- Tags: 

## Content

Tên đề tài luận án: Một số kỹ thuật nâng cao hiệu năng phần mềm nhúng trên bộ xử lý đa nhân 1. Họ và tên nghiên cứu sinh: Bùi Hữu Phúc                2. Giới tính: Nam 3. Ngày sinh: 18/09/1980                                               4. Nơi sinh: Hải Dương

5 Quyết định công nhận NCS: Số 642/QĐ-CTSV ngày 15 tháng 09 năm 2014 của Hiệu trưởng Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội.

6. Các thay đổi trong quá trình đào tạo: 7. Tên đề tài luận án: Một số kỹ thuật nâng cao hiệu năng phần mềm nhúng trên bộ xử lý đa nhân 8. Chuyên ngành: Kỹ thuật phần mềm                                               9. Mã số: 9480103.01 10. Cán bộ hướng dẫn khoa học: Hướng dẫn chính: PGS. TS. Nguyễn Ngọc Bình Cơ quan công tác: Trường Đại học CMC, Việt Nam Hướng dẫn phụ: TS. Lê Quang Minh Cơ quan công tác: Viện Công nghệ Thông tin – Đại học Quốc gia Hà Nội Thông tin luận án tiến sĩ của NCS Bùi Hữu Phúc ( tiếng Anh ) 11. Tóm tắt các kết quả mới của luận án:

Luận án cung cấp một mô hình tổng thể về vấn đề nâng cao hiệu năng trong phát triển phần mềm nhúng trên bộ xử lý đa nhân. Trong mô hình tổng thể, luận án đã trình bày vấn đề cải tiến phần mềm nhúng nhằm cải thiện hiệu năng dựa trên song song hóa tác vụ và song song hóa dữ liệu. Trong đó, tập trung vào xử lý song song hóa chức năng, song song hóa dữ liệu cũng như lựa chọn cấu trúc mã nguồn thích hợp và xử lý bất đồng bộ của các luồng thực thi trong phần mềm. Các kết quả chính của luận án được mô tả như sau:

Thứ nhất, vấn đề nâng cao hiệu năng dựa trên lựa chọn tác vụ xử lý chính để thực hiện song song:

– Luận án đã nghiên cứu theo hướng xử lý song song tác vụ với ý tưởng chính là phân chia chức năng tổng thể thành các tác vụ song song, phân phối tác vụ vào các nhân rỗi, lập lịch tác vụ và quản lý trao đổi thông tin giữa các tác vụ, chúng tôi đã phân chia chức năng tổng thể thành các tác vụ song song, tuy nhiên không phải tất cả các tác vụ song song đều đạt được hiệu năng cao hơn so với thực thi tuần tự, nên luận án lựa chọn dựa theo quy luật Pareto và đưa ra điều kiện ràng buộc số tác vụ được song song hóa;

– Luận án đưa ra phương pháp tìm cấu hình song song thích hợp cho mã nguồn dựa trên đánh giá cấu trúc và bộ tham số tương ứng và xây dựng mô hình tổng quát để triển khai ý tưởng. Luận án trình bày định nghĩa về cấu trúc song song, định nghĩa về cấu hình song song và xây dựng được điều kiện cấu hình song song qua hàm đánh giá hiệu năng và các công thức hỗ trợ tìm cấu hình thích hợp trong phương pháp.

Thứ hai, vấn đề nâng cao hiệu năng dựa trên xử lý song song hóa dữ liệu:

– Luận án nghiên cứu và phân chia dữ liệu cân bằng và phân bổ động nhằm song song hóa dữ liệu với mục đích cải tiến hiệu năng phần mềm nhúng, luận án đưa ra định nghĩa về bộ dữ liệu độc lập, bộ dữ liệu phụ thuộc và các bộ dữ liệu độc lập để xác định tham số, đưa ra công thức hỗ trợ phân luồng và tính được số luồng cũng như kích thước của dữ liệu cần xử lý;

– Đối với dữ liệu toàn cục hay dữ liệu không thể xác định độc lập, luận án xây dựng mô hình phân chia dữ liệu toàn cục dựa trên cấu hình các nhân của bộ xử lý và xử lý dữ liệu không đồng bộ giữa các luồng để cải tiến hiệu năng, luận án đã xây dựng mô hình tổng quát để phát triển phương pháp. Luận án đưa ra các định nghĩa về tỉ lệ theo tốc độ, tỉ lệ theo kích thước bộ nhớ đệm và tỉ lệ tổng hợp của các nhân trong bộ xử lý. Từ ba định nghĩa này, luận án xác định phân chia dữ liệu tới từng nhân tùy theo cách lựa chọn, công thức được xây dựng nhằm hỗ trợ phân chia xử lý dữ liệu theo cấu hình của từng nhân. Luận án cũng xử lý hạn chế của đồng bộ là chi phi thời gian chờ bằng cách sử dụng biến dùng chung và kiểm soát tính toán biến sau khi các luồng thực thi thực hiện xong.

Cuối cùng, luận án đã tiến hành cài đặt các bài toán từ phương pháp đề xuất để thực nghiệm, từ mô hình tổng quát, luận án xây dựng mô hình thực nghiệm và triển khai thực nghiệm để chứng minh các lý thuyết đưa ra là đúng. Kết quả nghiên cứu đã được trình bày trong các hội nghị, hội thảo và tạp chí khoa học chuyên ngành.

12. Khả năng ứng dụng trong thực tiễn.

Các kỹ thuật đã đề xuất trong luận án có thể được ứng dụng trong thực tế đối với các bài toán có cấu trúc rõ ràng, thực hiện các nhiệm vụ độc lập phù hợp với phần mềm nhúng. Ngoài ra, các kỹ thuật cũng đạt được hiệu quả với các bài toán xử lý các dữ liệu độc lập, đặc biệt trong truyền thông điệp trong các thiết bị nhúng IoT. Với các bài toán mã hóa cũng được phân tích và sử dụng phương pháp phân vùng dữ liệu và xử lý bất đồng bộ để tăng hiệu năng của phần mềm nhúng.

13. Những hướng nghiên cứu tiếp theo:

Trong thời gian tới, nghiên cứu sinh tập trung vào các nghiên cứu để giải quyết một số hạn chế còn tồn tại của luận án. Trong đó, tập trung tiến hành một số nghiên cứu sau đây:

– Tìm hàm đánh giá hiệu năng f j tổng quát để đưa ra lựa chọn cấu hình song song thích hợp;

– Cải tiến phương pháp ở một số khía cạnh: mở rộng vấn đề để xử lý dữ liệu đồng bộ; ánh xạ các luồng thực thi tới các nhân tương ứng; giám sát và thay đổi việc phân chia dữ liệu theo hiệu suất tại mỗi thời điểm khi mỗi nhân CPU xử lý xong dữ liệu.

14. Các công trình đã công bố có liên quan đến luận án: – B.H. Phúc, P.V. Hưởng và N.N. Bình, 2017, “ Một phương pháp cải thiện hiệu năng các ứng dụng Android trên chip đa nhân ”, Kỷ yếu Hội thảo khoa học FAIR 2017 – B.H. Phuc, P.V. Huong, N.N. Binh and L.Q. Minh, 2017, “

Enhancing the performance of Android applications on multi-core processors by selecting parallel configurations for source codes

”, pp. 225-229, 2017 4th NAFOSTED Conference on Information and Computer Science, DOI: 10.1109/NAFOSTED.2017.8108068 – B.H. Phuc, P.V. Huong, P.V. Quang, N.Q. Linh, 2018, “ Dynamic Threading to Improve Embedded Software Performance in IoT Devices Using MQTT Protocol

”, 2018 International Conference on Advanced Technologies for Communications, pp. 321-325, DOI: 10.1109/ATC.2018.8587511

– B.H. Phuc, H.T. Binh, L.Q. Minh, N.N. Binh, P.V. Huong, 2022, “ Data partitioning and asynchronous processing to improve the embedded software performance on multicore processors

”, Informatics and Automation journal (Scopus), Vol. 2, Issue 21, pp. 243–274, ISSN 2713-3192 (print), ISSN 2713-3206 (online), DOI: 10.15622/ia.21.2.2