# Thông tin luận án Tiến sỹ của NCS Đào Mạnh Hiệp

- ID: 49215
- Date: 2025-08-19T13:37:19
- URL: https://uet.edu.vn/thong-tin-luan-tien-sy-cua-ncs-dao-manh-hiep/
- Categories: Tiến sỹ
- Tags: 

## Content

Tên đề tài luận án: Nghiên cứu thiết kế bảo mật thẻ RFID sử dụng mã hoá đường cong Elliptic (Tiếng Anh: Security Lightweight RFID tag with Elliptic Curve Cryptography)

1. Họ và tên nghiên cứu sinh: Đào Mạnh Hiệp                                          2. Giới tính: Nam

3. Ngày sinh: 19/7/1995                                                                             4. Nơi sinh: TP. Hà Nội

5. Quyết định công nhận nghiên cứu sinh số 1344/QĐ-CTSV ngày 25 tháng 11 năm 2019 của Hiệu trưởng Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội.

6. Các thay đổi trong quá trình đào tạo: 7. Tên đề tài luận án: Nghiên cứu thiết kế bảo mật thẻ RFID sử dụng mã hoá đường cong Elliptic ( Tiếng Anh: Security Lightweight RFID tag with Elliptic Curve Cryptography ) 8. Ngành đào tạo: Kỹ thuật Điện tử                                                    9. Mã số: 9520203 10. Cán bộ hướng dẫn khoa học: Hướng dẫn chính: GS. TS Trần Xuân Tú Cơ quan công tác: Viện Công nghệ Thông tin, Đại học Quốc gia Hà Nội Hướng dẫn phụ: GS. TS Vincent Beroulle Cơ quan công tác: Đại học Grenoble Alpes, Cộng hoà Pháp Thông tin luận án Tiến sỹ của NCS Đào Mạnh Hiệp ( tiếng Anh ) 11. Tóm tắt các kết quả mới của luận án:

Công nghệ nhận dạng tần số vô tuyến thụ động (Passive RFID) mặc dù đã tạo ra bước đột phá và có vai trò quan trọng trong nhiều ứng dụng xác thực không dây, chúng vẫn phải đối mặt với nhiều lỗ hổng bảo mật bao gồm tấn công không dây và phần cứng. Để tăng tính bảo mật chống vấn đề chia sẻ khóa, việc tích hợp các cơ chế mật mã như Mật mã đường cong Elliptic (ECC) vào thẻ RFID thụ động là yếu tố then chốt để bảo vệ dữ liệu. Tuy nhiên, triển khai ECC trên thẻ RFID thụ động đặt ra những thách thức đáng kể như sau:

Hạn chế về tài nguyên vật lý: Thẻ RFID thụ động chịu ràng buộc nghiêm ngặt về tiêu thụ năng lượng, diện tích và độ trễ bởi tiêu chuẩn ISO/IEC-14443.

Yêu cầu bảo mật: Các biện pháp bảo vệ thẻ RFID thụ động trước tấn công không dây và phần cứng làm tăng độ phức tạp xử lý. Hệ quả là chi phí triển khai hệ thống tăng đáng kể.

Bên cạnh đó, quá trình thiết kế nhằm triển khai giao thức xác thực sử dụng thuật toán mã hóa đường cong ECC trải qua nhiều tầng thiết kế với hàng loạt lựa chọn về kiến trúc hệ thống, thuật toán thực hiện. Điều này khiến không gian thiết kế của hệ thống trở nên phức tạp, làm tăng thời gian nghiên cứu sản xuất và chi phí phát triển sản phẩm.

Vì vậy, những vấn đề trên thúc đẩy nghiên cứu nhằm phát triển quy trình thiết kế mới giúp người thiết kế cân bằng giữa chi phí thực thi và tính bảo mật của hệ thống nhờ đồng thời đánh giá cả hai yếu tố trên trong từng giai đoạn thiết kế. Bên cạnh đó, quy trình thiết kế mới cũng cần giảm thời gian thiết kế nhằm tối ưu chi phí nghiên cứu phát triển sản phẩm.

Nhằm giải quyết những vấn đề trên, nghiên cứu đã đề xuất những đóng góp chính sau:

Một kiến trúc phần cứng BEC tiết kiệm chi phí và tiêu thụ điện năng thấp với quy mô 21,68 kGates logic đã được đề xuất và tổng hợp bằng công nghệ CMOS TSMC 65nm, theo phương pháp thiết kế Top-down truyền thống. Cấu trúc phần cứng đề xuất tiêu thụ công suất 126μW tại 10MHz, được ước tính bằng công cụ Synopsys PrimeTime. Kết quả triển khai phần cứng cho thấy hệ thống đề xuất của chúng tôi hiệu quả về mặt chi phí triển khai và tiêu thụ năng lượng khi so sánh với các công trình khác. Bên cạnh đó, đánh giá TVLA chứng minh rằng đề xuất có khả năng chống lại lỗ hổng bảo mật kênh bên.

Đề xuất phương pháp luận thiết kế đánh giá sớm EEMitM (Early Evaluation Meet-in-the-Middle) giúp tối ưu hóa đa mục tiêu trong không gian thiết kế rộng. Bằng cách sử dụng cơ sở dữ liệu của các nguyên thủ bảo mật tham chiếu, các nhà thiết kế có thể mô hình hóa hệ thống được chọn mà không cần tạo nguyên mẫu. Khung làm việc được đề xuất cho phép mô hình hóa nhanh chóng trong môi trường phần mềm, từ đó giảm đáng kể thời gian đưa sản phẩm ra thị trường. Các thí nghiệm cho thấy, khi áp dụng đề xuất này, thời gian phát triển sản phẩm giảm 480 lần so với quy trình thiết kế truyền thống. Về độ chính xác trong việc ước lượng chi phí triển khai, các thí nghiệm cho thấy sai số về độ trễ chỉ 1,2%. Trong trường hợp ước lượng tiêu thụ điện năng kém nhất, độ chính xác vẫn duy trì ở mức sai số chấp nhận được là 22,6%.

12. Khả năng ứng dụng trong thực tiễn:

Ứng dụng trong các ứng dụng thẻ mã hoá xác thực RFID thụ động như Căn cước công dân điện tử, thẻ thanh toán không chạm, hay hộ chiếu điện tử.

Phương pháp luận thiết kế EEMitM bước đầu giải quyết được một số thách thức then chốt trong việc khám phá không gian thiết kế cho các giao thức xác thực sử dụng thuật toán mã hóa đường cong Elliptic cho thẻ RFID thụ động, khởi đầu cho nhiều hướng nghiên cứu mở có thể tiếp tục phát triển.

13. Những hướng nghiên cứu tiếp theo:

Đánh giá tính bảo mật của đề xuất phần cứng công suất thấp, chi phí thấp BEC với các mối đe doạ tấn công phần cứng cụ thể, như phân tích công suất tương quan (CPA) hay phân tích công suất vi sai (DPA).

Phát triển phương pháp luận thiết kế thành các công cụ thiết kế tự động (EDA) với giao diện người dùng (GUI). Mở rộng cơ sở dữ liệu ứng cho nhiều ứng dụng đặc thù. 14. Các công trình đã công bố có liên quan đến luận án: Manh-Hiep Dao

, Vincent Beroulle, Yann Kieffer, and Xuan-Tu Tran. “How to Develop ECC-Based Low-Cost RFID Tags Robust Against Side-Channel Attacks.” In International Conference on Industrial Networks and Intelligent Systems, pp. 433-447. Cham: Springer International Publishing, 2021.

Souhir Gabsi, Vincent Beroulle, Yann Kieffer, Manh-Hiep Dao

, Yassin Kortli, and Belgacem Hamdi. “Survey: Vulnerability analysis of low-cost ECC-based RFID protocols against wireless and side-channel attacks.” Sensors 21, no. 17 (2021): 5824.

Manh-Hiep Dao

, Vincent Beroulle, Yann Kieffer, and Xuan-Tu Tran (2023). “Secure-by-Design methodology using Meet-in-the-Middle design flow for hardware implementations of ECC-based passive RFID tags”. In ICWMC 2023, The Nineteenth International Conference on Wireless and Mobile Communications. IARIA (pp. 14-19).

Manh-Hiep Dao

, Vincent Beroulle, Yann Kieffer, Xuan-Tu Tran, and Duy-Hieu Bui. “Low-cost Low-Power Implementation of Binary Edwards Curve for Secure Passive RFID Tags.” In 2023 IEEE 16th International Symposium on Embedded Multicore/Many-core Systems-on-Chip (MCSoC), pp. 494-500. IEEE, 2023