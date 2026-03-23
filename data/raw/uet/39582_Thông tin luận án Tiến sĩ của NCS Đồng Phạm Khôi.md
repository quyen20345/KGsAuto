# Thông tin luận án Tiến sĩ của NCS Đồng Phạm Khôi

- ID: 39582
- Date: 2023-12-05T14:50:16
- URL: https://uet.edu.vn/thong-tin-luan-tien-si-cua-ncs-dong-pham-khoi/
- Categories: Đào tạo sau Đại học
- Tags: 

## Content

Tên đề tài luận án: Giải pháp kiến trúc phần cứng bảo mật AES hiệu quả cao, công suất thấp dùng cho các thiết bị internet vạn vật.

1. Họ và tên nghiên cứu sinh: Đồng Phạm Khôi…………… 2. Giới tính: Nam………………….. 3. Ngày sinh: 12/07/1982………………………………………….. 4. Nơi sinh: Thanh Hóa………….

5. Quyết định công nhận nghiên cứu sinh số:654/QĐ-CTSV, ngày 05 tháng 09 năm 2016 của Hiệu trưởng trường Đại học Công nghệ.

6. Các thay đổi trong quá trình đào tạo: ………………………………………………………………………

7. Tên đề tài luận án:Giải pháp kiến trúc phần cứng bảo mật AES hiệu quả cao, công suất thấp dùng cho các thiết bị internet vạn vật.

8. Chuyên ngành:Kỹ thuật điện tử……………………………… 9. Mã số:9510302.01……………. 10. Cán bộ hướng dẫn khoa học: PGS. TS. Trần Xuân Tú…………………………………………….. Thông tin luận án Tiến sĩ của NCS Đồng Phạm Khôi ( tiếng Anh ) 11. Tóm tắt các kết quả mới của luận án:

Đề xuất kiến trúc phần cứng AES đơn lõi phù hợp với các ứng dụng thông lượng cao và yêu cầu thời gian thực. Kiến trúc mã hóa song song và kỹ thuật đường ống được sử dụng trong thiết kế bộ mã hóa AES giúp tăng tốc độ mã hóa và giảm độ trễ. Kết quả thực thi phần cứng trên công nghệ CMOS 45nmcủa NANGATE cho thấy thiết kế có thể hoạt động ở tần số tối đa 870

MHz và đạt được thông lượng cao 111,3 Gbps và có độ trễ thấp (12,6 ns ) trong khi có hiệu quả sử dụng diện tích (856 Gbps/mm 2 ) và hiệu quả sử dụng năng lượng (1977 Gbps/W ). Các kết quả này đã được công bố tại Hội nghị IEEE ISCIT 2019 (công trình [C1]).

Đề xuất kiến trúc phần cứng mã hóa đa lõi song song có thông lượng mã hóa cao (MCryptCores).Với kiến trúc này, khối KeyExpansion được chia sẻ giữa các lõi AES để giảm thiểu chi phí về diện tích triển khai phần cứng và công suất tiêu thụ. Kết quả thực thi phần cứng chứng minh rằng thiết kế phần cứng đạt được thông lượng lên tới 1

Tbps

với 10 lõi AES trên chip. Với 10 lõi AES, hiệu quả sử dụng năng lượng lớn hơn 20% và hiệu quả sử dụng diện tích lớn hơn 28% so với kiến trúc lõi đơn. Mặt khác, thông lượng cao trong thiết kế cũng đáp ứng các yêu cầu bảo mật dữ liệu trong các tiêu chuẩn truyền thông mới như IEEE P802.3bm 2015, với tốc độ 100

Gbps hoặc IEEE P802.3bs 2017 có tốc độ truyền dữ liệu lên đến 400 Gbps

. Các kết quả đã được công bố tại Hội nghị IEEE APCCAS 2020 (công trình [C2]) và trên Tạp chí Khoa học JCSCE (công trình [J1]).

Thiết kế nền tảng mã hóa đa lõi Spike-MCryptCores với bộ điều khiển nơ-ron xung công suất thấp. Spike-MCryptCores bao gồm phần mềm cho phép thiết kế, huấn luyện và kiểm tra bộ điều khiểnSNN và phần cứng bao gồm nhiều lõi AES được điều khiển ngắt xung đồng hồ bởi phần cứng SNN. Phần mềm huấn luyện cho SNN đạt được độ chính xác hơn 95% chỉ với một lớp ẩn duy nhất gồm 5 nơ-ron. Trong trường hợp đoán sai sự sai khácchỉ là một lõi so với nhãn, khi đó các bộ đệm đầu vào và đầu ra sẽ giúp tránh mất mát dữ liệu. Phần cứng của bộ điều khiển SNN chỉ chiếm 2,3% diện tích của hệ thống nhưng giúp hệ thống có thể giảm công suất tiêu thụ từ 39% đến 67%. Với Spike-McryptCores luận án đã giới thiệu một phương pháp mới để thiết kế và điều khiển các hệ thống đa lõi với chi phí cực nhỏ và độ chính xác cao. Các kết quả này đã được gửi công bố trên tạp chí Microprocessors and Microsystems (công trình [J2]).

12. Khả năng ứng dụng trong thực tiễn:Các kết quả của luận án có thể được ứng dụng để bảo mật bằng phần cứng với hiệu quả cao, công suất tiêu thụ thấp cho các thiết bị IoT.

13. Những hướng nghiên cứu tiếp theo: – Áp dụng mô hình Spike-MCryptCores cho các loại ứng dụng đa lõi khác.

– Sử dụng Spike-MCryptCores cho các kỹ thuật công suất thấp khác như ngắt nguồn nuôi hoặc phân chia tỷ lệ tần số điện áp động.

14. Các công trình đã công bố có liên quan đến luận án:

[C1]  Pham-Khoi Dong, H. K. Nguyen, and Xuan-Tu Tran, “A 45nm High-Throughput and Low Latency AES Encryption for Real-Time Applications,” in 2019

19th International Symposium on Communications and Information Technologies (ISCIT), Sep. 2019, pp. 196–200. doi: 10.1109/ISCIT.2019.8905235.

[C2]  Pham-Khoi Dong, H. K. Nguyen, Van-Phuc Hoang, and Xuan-Tu Tran, “Low-Power Implementation of a High-Throughput Multi-core AES Encryption Architecture,” in

2020 IEEE Asia Pacific Conference on Circuits and Systems (APCCAS) , Dec. 2020, pp. 74–77. doi: 10.1109/APCCAS50809.2020.9301668.

[J1]   Pham-Khoi Dong, H. K. Nguyen, F. A. Hussin, and Xuan-Tu Tran, “Ultra-High-Throughput Multi-Core AES Encryption Hardware Architecture,”

VNU J. Sci. Comput. Sci. Commun. Eng. , vol. 37, Nov. 2021, doi: 10.25073/2588-1086/vnucsce.290.

[J2]    Pham-Khoi Dong, Khanh N. Dang, Duy-Anh Nguyen, and Xuan-Tu Tran, “A light-weight neuromorphic controlling clockgating based multi-core cryptography platform”

Microprocessors and Microsystems , resubmitting.