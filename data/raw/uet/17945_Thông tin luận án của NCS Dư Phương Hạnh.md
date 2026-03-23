# Thông tin luận án của NCS Dư Phương Hạnh

- ID: 17945
- Date: 2019-08-26T14:58:50
- URL: https://uet.edu.vn/thong-tin-luan-cua-ncs-du-phuong-hanh/
- Categories: Tiến sỹ
- Tags: 

## Content

Tên đề tài luận án: Nâng cao hiệu năng thi hành các phép toán trên đồ thị 1. Họ và tên nghiên cứu sinh: Dư Phương Hạnh             2. Giới tính: Nữ 3. Ngày sinh: 29/05/1979.                                                 4. Nơi sinh: Hà Nội 5. Quyết định công nhận nghiên cứu sinh số:67/QĐ-ĐT ngày 24 tháng 01 năm 2014 của Trường ĐH Công Nghệ. 6. Các thay đổi trong quá trình đào tạo: Không 7. Tên đề tài luận án: Nâng cao hiệu năng thi hành các phép toán trên đồ thị. 8. Chuyên ngành:CNTT                                                    9. Mã số:62 48 01 04 10. Cán bộ hướng dẫn khoa học: PGS.TS. Nguyễn Hải Châu PGS. TS. Nguyễn Kim Khoa 11. Tóm tắt các kết quả mới của luận án:

– Giải pháp 1: khai thác các hệ thống tính toán có dung lượng bộ nhớ chính lớn và các bộ vi xử lý nhiều lõi, với ba ý tưởng chính: tổ chức dữ liệu đồ thị thích hợp để tăng tốc độ truy cập trong bộ đệm CPU; giảm thiểu không gian tìm kiếm bằng cách lựa hướng duyệt có số lượng con và cháu ít hơn đối với thuật toán duyệt hai chiều bBFS; và thi hành các truy vấn khoảng cách ngắn nhất một cách hiệu quả thông qua phương pháp xử lý song song dựa vào bộ thư viện Cilkplus. Ở giải pháp này, dữ liệu đồ thị được tổ chức trên hai mảng chứa toàn bộ các đỉnh liền kề và hai mảng chỉ mục để lưu số đỉnh liền kề và vị trí bắt đầu trong mảng dữ liệu đồ thị. Cách tổ chức này được tiến hành đối với cả chiều đi  và chiều đến để cho phép có thể tiến hành tính khoảng cách ngắn nhất dựa theo duyệt BFS cả hai chiều. Kết quả này được chúng tôi công bố trong công trình tại hội thảo BDCAT về quản lý dữ liệu lớn năm 2016.

– Dựa trên giải pháp 1, chúng tôi đãđề xuất giải pháp 2 với mô hình tổ chức dữ liệu đồ thị khác đi: nhúng kèm trạng thái cạnh đồ thị (sử dụng 2 bits cuối của định danh đỉnh liền kề). Với cách tổ chức dữ liệu này, việc thi hành toàn bộ các truy vấn khoảng cách trong lịch thi hành S được tập hợp lại và xử lý song song trên hệ thống tính toán. Từ đó, hiệu năng của quá trình xử lý S đãđược cải thiện như minh chứng trong thực nghiệm thứ 2 của chúng tôi. Giải pháp này của chúng tôi cũng đãđược công bố tại hội thảo quốc tế ICCCI năm 2017.

– Giải pháp 3: chúng tôi đãđề xuất kỹ thuật cho phép tiến hành song song các phép toán cập nhật với ý tưởng: có thể tiến hành song song các phép toán cập nhật trên các danh sách đỉnh liền kề khác nhau. Các thực nghiệm được chúng tôi tiến hành với giải pháp này cũng đã minh chứng được hiệu quả của quá trình song song cả các phép cập nhật lẫn tính khoảng cách ngắn nhất. Kết quả này cũng được chúng tôi công bố trong tạp chí quốc tế Transactions on Computational Collective Intelligence, Springer, năm 2018.

– Về những đóng góp trong việc tính hai độ đo trung tâm trên đồ thị, giải thuật tính độ trung tâm gần mà chúng tôi đề xuất, được cài đặt trong BigGraph, dựa trên ý tưởng: (i) sử dụng cấu trúc dữ liệu phù hợp để nâng cao tính cục bộ dữ liệu, từ đó nâng cao tỷ lệ cache hit trong mô hình bộ nhớ chia sẻ, nâng cao hiệu năng truy xuất bộ nhớ; (ii) áp dụng giải thuật duyệt theo chiều rộng trước đối với tất cả các đỉnh, kết hợp với kỹ thuật sử dụng mảng bitmaps để giảm thiểu thời gian truy xuất kiểm tra đỉnh đã duyệt trong hàng đợi; và (iii) song song hoá các phép tính tại các đỉnh với mô hình lập trình luồng sử dụng bộ thư viện CilkPlus. Các kết quả thực nghiệm cho thấy BigGraph có hiệu năng nhanh hơn TeexGraph và NetworKit lần lượt từ 1,27 đến 2,12 và 14,78 đến 68,21 lần. Các kết quả này của chúng tôi đãđược nhận đăng và sẽ được công bố trong kỷ yếu hội thảo SoICT năm 2018 (cũng nằm trong chỉ mục SCOPUS). Đối với việc tính toán độ trung tâm giữa, chúng tôi đã xây dựng giải pháp song song hoá giải thuật Brandes cũng dựa trên ý tưởng tổ chức dữ liệu hợp lý kết hợp cùng kỹ thuật tính toán song song sử dụng thư viện CilkPlus. Kết quả thực nghiệm đã thể hiện được giải thuật tính độ trung tâm giữa trong BigGraph của chúng tôi cho hiệu năng thi hành tốt hơn so với hai bộ công cụ TeexGraph và NetworKit lần lượt từ 1,11 đến 1,35 và từ 2,06 đến 2,44 lần

12. Khả năng ứng dụng trong thực tiễn: ( nếu có )

13. Những hướng nghiên cứu tiếp theo: Nghiên cứu làm chủ những công nghệ xử lý đối với quy mô dữ liệu đồ thị siêu lớn; tiến hành cài đặt bộ công cụ hoàn chỉnh để phân tích đồ thị và tính toán các độ đo trung tâm; nghiên cứu chuyên sâu hơn trong tối ưu hóa xử lý các truy vấn trên đồ thị thuộc tính, cho phép xử lý hiệu quả hơn các truy vấn trên đồ thị động, thay đổi theo thời gian.

14. Các công trình đã công bố có liên quan đến luận án:

1. Phuong-Hanh DU, Hai-Dang Pham, Ngoc-Hoa Nguyen, “Optimizing the Shortest Path Query on Large-Scale Dynamic Directed Graph”, BDCAT ’16 Proceedings of the 3rd IEEE/ACM International Conference on Big Data Computing, Applications and Technologies, pp210-216, 2016. (SCOPUS, WoS)

2. Phuong-Hanh DU, Hai-Dang Pham, Ngoc-Hoa Nguyen, “An Efficient Parallel Method for Performing Concurrent Operations on Social Networks”, Computational Collective Intelligence, Volume 10448 of the series Lecture Notes in Computer Science, Springer, pp 148-159, 2017. (SCOPUS, WoS)

3. Phuong-Hanh DU, Hai-Dang Pham, Ngoc-Hoa Nguyen, “An Efficient Parallel Method for Optimizing Concurrent Operations on Social Networks”, Transactions on Computational Collective Intelligence. Lecture Notes in Computer Science, vol 10840, no XXIX, pp. 182-199. Springer 2018, ISSN 2190-9288. (SCOPUS, WoS)

4. Phuong-Hanh DU, Hai-Chau NGUYEN, Kim-Khoa NGUYEN, and Ngoc-Hoa NGUYEN.“An Efficient Parallel Algorithm for Computing the Closeness Centrality in Social Networks”. In The Ninth International Symposium on Information and Communication Technology (SoICT 2018), pp. 456-462, December, 2018. ACM, USA. (SCOPUS, WoS)