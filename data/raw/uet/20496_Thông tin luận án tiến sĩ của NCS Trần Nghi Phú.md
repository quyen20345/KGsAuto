# Thông tin luận án tiến sĩ của NCS Trần Nghi Phú

- ID: 20496
- Date: 2020-06-08T10:27:09
- URL: https://uet.edu.vn/thong-tin-luan-tien-si-cua-ncs-tran-nghi-phu/
- Categories: Tiến sỹ
- Tags: 

## Content

Tên đề tài luận án: Phân tích tự động mã độc trong các thiết bị nhúng trên nền Linux 1. Họ và tên nghiên cứu sinh: Trần Nghi Phú……………..               2. Giới tính: Nam………………….. 3. Ngày sinh: 07/11/1987…………………………………………..              4. Nơi sinh: Nghệ An……………..

5. Quyết định công nhận nghiên cứu sinh số: 361/QĐ-ĐT ngày 13 tháng 06 năm 2014 của Hiệu Trưởng Trường Đại học Công nghệ – Đại học Quốc gia Hà Nội.

6. Các thay đổi trong quá trình đào tạo: 7. Tên đề tài luận án: Phân tích tự động mã độc trong các thiết bị nhúng trên nền Linux . 8. Chuyên ngành: Kỹ thuật phần mềm………………………..                                9. Mã số: 9480103.01…………… 10. Cán bộ hướng dẫn khoa học: PGS.TS. Nguyễn Ngọc Bình, TS. Nguyễn Đại Thọ 11. Tóm tắt các kết quả mới của luận án: ……………………………………………………………………

Thứ nhất, xây dựng cơ sở dữ liệu về phần sụn của các thiết bị IoT và mã độc trên IoT, gọi là tập dữ liệu Firmware IoT (F-IoT).

Đây là cơ sở dữ liệu có số lượng lớn và khá đầy đủ về các phần sụn, mã độc và mã sạch trên thiết bị IoT. Để xây xây dựng cơ sở dữ liệu này, luận án phát triển công cụ F-Toolkit hỗ trợ việc thu thập, phân tích, bóc tách phần sụn.

Thứ hai, phát triển môi trường phân tích động F-Sandbox cùng hai quy trình phát hiện và phân lớp mã độc nhúng.

Đây là loại sandbox mới, chuyên dụng cho các thiết bị IoT dựa trên hệ điều hành Linux nhúng. F-Sandbox được phát triển dựa trên QEMU, kế thừa các kỹ thuật của Firmadyne cho phép mô phỏng NVRAM, mạng Internet và trích xuất các lời gọi hệ thống (System call – syscall) dựa trên nhân Linux 2.6 được sửa đổi (instrumented kernel).

Thứ ba, đề xuất thuật toán cải tiến để trích xuất đặc trưng dựa trên luồng điều khiển (Control flow-based feature).

Bài toán trích xuất đặc trưng dựa trên luồng điều khiển được chuyển thành bài toán tính tổng số đường đi từ đỉnh gốc đến các lá trên đồ thị có hướng không có chu trình. Đồ thị trọng số tổng số đường đi này được xây dựng dựa trên ý tưởng phương pháp quy hoạt động với độ phức tạp đa thức, thay cho phương pháp duyệt theo chiều sâu (là bài toán NP-Hard) của Ding và cộng sự đề xuất. Cải tiến này vừa nâng cao hiệu quả cho các mẫu có kích thước lớn và độ phức tạp cao trên môi trường máy vi tính truyền thống và rất thích hợp cho mã độc trên thiết bị nhúng vốn đa phần sử dụng các kiến trúc vi xử lý RISC nên đồ thị luồng điều khiển thu được có số lượng đỉnh lớn hơn các kiến trúc vi xử lý có kiến trúc CISC như máy vi tính truyền thống.

Thứ tư, đề xuất phương pháp trích chọn đặc trưng để phát hiện mã độc đa kiến trúc vi xử lý CFGVex .

Phương pháp trích chọn đặc trưng CFGVex được đề xuất trên cơ sở thuật toán quy hoạch động đã đề xuất của luận án, đã đạt hiệu quả cao với mã độc trên thiết bị nhúng trên một kiến trúc, kết hợp với ngôn ngữ trung gian Vex thay cho opcode để phát hiện mã độc đa kiến trúc vi xử lý. Phương pháp này cho phép học tri thức các mã độc trên kiến trúc cũ để phát hiện mã độc trên kiến trúc vi xử lý mới, đây là một trong những xu thế xuất hiện của mã độc trên thiết bị nhúng. Luận án đề xuất và lựa chọn cách lấy đặc trưng phù hợp để cho khả năng phát hiện mã độc tốt nhất. Thực nghiệm cho thấy, CFGVex có khả năng phát hiện mã độc đa nền tảng độ chính xác cao, mở ra hướng nghiên cứu để xác định mối liên hệ chuyển dịch giữa mã độc trên các kiến trúc khác nhau, giữa mã độc truyền thống trên máy vi tính sang mã độc trên thiết bị nhúng.

12. Khả năng ứng dụng trong thực tiễn: Các kết quả của luận án có thể áp dụng để phát triển các sản phẩm kiểm định phần sụn các thiết bị nhúng, phát hiện mã độc hoạt động trên các thiết bị nhúng.

13. Những hướng nghiên cứu tiếp theo: Tiếp tục hoàn thiện F-Sandbox để kích hoạt một số mẫu mã độc, chương trình mang tính đặc thù cao; phát triển công cụ F-Toolkit có khả năng phân tích các bản ảnh ở dạng không đầy đủ; cải tiến nâng cao hiệu quả CFDVex để phát hiện mã độc đa kiến trúc; pháp triển các phương pháp loại bỏ mã độc khỏi phần sụn của thiết bị IoT.

14. Các công trình đã công bố có liên quan đến luận án: 1. Tran Nghi Phu, Nguyen Ngoc Binh, Hoang Dang Kien, Ngo Quoc Dung,

Nguyen Dai Tho. A Novel Framework to Classify Malware in MIPS Architecture-based IoT Devices. Security and Communication Networks,

2019, 13 pages, https://doi.org/10.1155/2019/4073940 (ISI, SCIE index). 2. Tran Nghi Phu, Nguyen Dai Tho, Le Huy Hoang, Nguyen Ngoc Binh. An Efficient Algorithm to Extract Control Flow-based Features for IoT Malware Detection . Computer Journal, 2020 (Accepted, ISI, SCIE index). 3. Tran Nghi Phu, Ngo Quoc Dung, Le Van Hoang, Nguyen Dai Tho,

Nguyen Ngoc Binh. A System Emulation for Malware Detection in Routers. International Journal of Innovative Technology and Exploring

Engineering (IJITEE) ISSN: 2278-3075, Volume-8, Issue-11, Sep 2019 (Scopus index). 4. Trần Nghi Phú, Ngô Quốc Dũng, Hoàng Đăng Kiên, Nguyễn Đại Thọ, Nguyễn Ngọc Bình. Phát Hiện Mã Độc Trên Các Thiết Bị IoT Dựa Trên Lời Gọi Syscall và Phân Lớp Một Lớp SVM . Tạp chí Thông Tin và Truyền Thông, ISSN 1859-3550, 12-2018.

5. Tran Nghi Phu, Nguyen Ngoc Binh, Ngo Quoc Dung, and Le Van Hoang. Towards Malware Detection in Routers with C500-Toolkit. 5th International Conference on Information and Communication Technology (ICoICT), 1–5, 2017.

https://doi.org/10.1109/ICoICT.2017.8074691 (Scopus index). 6. Tran Nghi Phu, Nguyen Ngoc Binh, Nguyen Dai Tho, Nguyen Ngoc Toan, and Le Huy Hoang. CFDVex: A Novel Feature Extraction Method for Detecting Cross-Architecture IoT Malware

. The tenth international Symposium on Information and Communication Technology (SoICT 2019), Dec-2019, Hanoi, Vietnam, pp.248-254 (Scopus index).

7. Tran Nghi Phu, Nguyen Ngoc Toan, Le Huy Hoang, Nguyen Dai Tho, Nguyen

Ngoc Binh. C500-CFG: A Novel Algorithm to Extract Control Flow-based Features for IoT Malware Detection. 19th International Symposium on Communications and Information Technologies (ISCIT), 2019, HCM, Vietnam.

8. Trần Nghi Phú, Ngô Quốc Dũng, Nguyễn Huy Trung, Nguyễn Ngọc Bình. Mô Hình Phát Hiện Mã Độc trong Phần Mềm Nhúng trên Thiết Bị Định Tuyến . Hội Thảo Quốc Gia Lần Thứ XIX: Một số vấn đề chọn lọc của CNTT&TT, Hà Nôi, 2016. 9. Trần Nghi Phú, Nguyễn Huy Trung, Ngô Quốc Dũng, Nguyễn Ngọc Bình, and Nguyễn Đại Thọ. Phát Triển Công Cụ Dịch Ngược Firmware Trên Thiết Bị Định Tuyến . Hội Nghị Khoa Học Hội Thảo Lần Thứ I: Một số vấn đề chọn lọc về An toàn thông tin, 9-2016.