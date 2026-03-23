# Thông tin luận án Tiến sỹ của NCS Phạm Hải Đăng

- ID: 50478
- Date: 2025-09-25T08:45:07
- URL: https://uet.edu.vn/thong-tin-luan-tien-sy-cua-ncs-pham-hai-dang/
- Categories: Tiến sỹ
- Tags: 

## Content

Tên đề tài luận án: Nghiên cứu, phát triển phương pháp học máy hiện đại để nâng cao hiệu năng tái định danh người. 1. Họ và tên nghiên cứu sinh: Phạm Hải Đăng                       2. Giới tính: Nam 3. Ngày sinh: 25-08-1991                                                4. Nơi sinh: Hà Nội

5. Quyết định công nhận nghiên cứu sinh số: 1200/CTSV, ngày 29 tháng 12 năm 2020 của Hiệu trưởng Trường Đại học Công nghệ, Đại học Quốc gia Hà Nội.

6. Các thay đổi trong quá trình đào tạo: Điều chỉnh tên đề tài luận án theo quyết định số 1477/QĐ-ĐHCN ngày 11/07/2025 của Hiệu trưởng trường Đại học Công nghệ.

7. Tên đề tài luận án: Nghiên cứu, phát triển phương pháp học máy hiện đại để nâng cao hiệu năng tái định danh người. 8. Ngành đào tạo: Hệ thống thông tin                                  9. Mã số: 9480104 10. Cán bộ hướng dẫn khoa học: PGS.TS Nguyễn Ngọc Hóa – Trường ĐHCN. PGS.TS Nguyễn Ngọc Tú – Kennesaw State University. Thông tin luận án Tiến sỹ của NCS Phạm Hải Đăng  ( tiếng Anh ) 11. Tóm tắt các kết quả mới của luận án: 11.1 Mục đích và đối tượng nghiên cứu của luận án.

Trong bối cảnh đô thị hóa mạnh mẽ và quá trình chuyển đổi số diễn ra ngày càng sâu rộng, hệ thống camera giám sát đã trở thành một công cụ không thể thiếu trong việc đảm bảo an ninh, duy trì trật tự xã hội và theo dõi hành vi trong các không gian công cộng. Tuy nhiên, với số lượng camera không ngừng gia tăng, việc giám sát và phân tích dữ liệu hình ảnh một cách thủ công bởi con người ngày càng trở nên không khả thi và kém hiệu quả. Thực tế này đặt ra yêu cầu cấp thiết đối với các giải pháp giám sát tự động hóa, trong đó nổi bật là bài toán tái định danh người (Person Re-identification) nhằm xác định và nhận diện lại một người xuất hiện ở nhiều camera khác nhau, bất chấp sự thay đổi về góc nhìn, điều kiện ánh sáng, trang phục hoặc môi trường quan sát. Việc giải quyết hiệu quả bài toán này không chỉ góp phần nâng cao khả năng phản ứng kịp thời mà còn hỗ trợ quá trình điều tra và đảm bảo an ninh trong các hệ thống giám sát quy mô lớn. Chính từ những yêu cầu thực tiễn nêu trên, mục đích hướng đến của luận án là nghiên cứu, phát triển các phương pháp học máy hiện đại để nâng cao hiệu năng tái định danh người theo ba định hướng cụ thể: học có giám sát, học thích ứng miền không giám sát và học không giám sát hoàn toàn.

Đối tượng nghiên cứu: ảnh, tập ảnh từ các camera giám sát, cụ thể là từ các bộ dữ liệu chuẩn như CUHK03, Market-1501, DukeMTMC-reID, MSMT17; hệ thống, mô hình, phương pháp, thuật toán học sâu áp dụng cho bài toán tái định danh người.

. 11.2 Các phương pháp nghiên cứu đã sử dụng

Phương pháp lý thuyết: Nghiên cứu nền tảng về học sâu và tái định danh người, tập trung vào các kỹ thuật như học có giám sát, học không giám sát, học thích ứng miền không giám sát, thuật toán phân cụm và gán nhãn giả, nhằm xây dựng cơ sở khoa học cho đề xuất mô hình.

Phân tích và tổng hợp: Thu thập, đánh giá các công trình, mã nguồn và kết quả thực nghiệm trước đó để xác định xu hướng nghiên cứu và làm cơ sở đề xuất hướng cải tiến.

Mô hình hóa: Xây dựng mô hình bài toán tái định danh dưới dạng hệ thống gồm ảnh đầu vào, khối trích xuất đặc trưng, không gian nhúng và hàm đo tương đồng, hỗ trợ thử nghiệm và triển khai.

Thực nghiệm: Thử nghiệm trên các bộ dữ liệu chuẩn (CUHK03, Market-1501, DukeMTMC-reID, MSMT17), đánh giá bằng các chỉ số CMC (Rank-n) và mAP, và so sánh với các phương pháp hiện tại.

11.3 Các kết quả chính và kết luận Theo hướng tiếp cận học có giám sát, đề xuất phương pháp SCM-ReID

sử dụng hàm mất mát tương phản có giám sát kết hợp với bốn hàm mất mát phổ biến (phân loại, bộ ba, trung tâm, bộ ba trọng tâm) giúp mô hình học được đặc trưng có tính phân biệt và khả năng khái quát tốt hơn.

Theo hướng tiếp cận học thích ứng miền không giám sát, đề xuất phương pháp IQAGA và DAPRH

bằng cách kết hợp các chiến lược: thu hẹp khoảng cách phân phối giữa hai miền thông qua GAN và ánh xạ bất biến miền (DIM), đánh giá chất lượng ảnh để điều chỉnh trọng số huấn luyện, tích hợp đặc trưng cục bộ và toàn cục để tăng tính biểu diễn, và tinh chỉnh nhãn giả mềm dựa trên khoảng cách tâm cụm nhằm nâng cao độ ổn định và độ chính xác.

Trong hướng tiếp cận học không giám sát đề xuất phương pháp ViTC-UReID

tận dụng kiến trúc ViT thay thế CNN để tăng cường biểu diễn đặc trưng toàn cục, đồng thời tích hợp thông tin camera nhằm học đặc trưng phù hợp với từng góc nhìn, từ đó cải thiện hiệu năng tái định danh người không giám sát.

12. Khả năng ứng dụng trong thực tiễn: Kết quả của luận án mang lại nhiều ứng dụng thiết thực trong các hệ thống giám sát thông minh. Nhờ khả năng liên kết danh tính của cùng một cá nhân qua một hoặc nhiều camera khác nhau, hệ thống có thể truy xuất chính xác lịch sử di chuyển, hỗ trợ phân tích hành vi trong bối cảnh không gian – thời gian, và kết hợp dữ liệu từ nhiều nguồn quan sát thành một bức tranh toàn diện. Điều này giúp các cơ quan chức năng giám sát hiệu quả hơn tại sân bay, nhà ga, trung tâm thương mại hay khu vực công cộng đông người. Trên thực tế, tại những khu vực được triển khai công nghệ này, tái định danh người đã góp phần quan trọng trong hệ thống giám sát thông minh để việc phát hiện sớm hành vi bất thường, giảm tỷ lệ tội phạm và nâng cao mức độ an toàn xã hội.

13. Những hướng nghiên cứu tiếp theo: Thứ nhất, áp dụng hoặc kết hợp linh hoạt các hàm mất mát mới để tối ưu hóa không gian đặc trưng và tăng khả năng phân biệt danh tính. Thứ hai, cải thiện chất lượng ảnh sinh thông qua GAN bằng các ràng buộc hợp lý, hoặc thay thế bằng các kỹ thuật tăng cường dữ liệu tiên tiến hơn như mô hình khuếch tán nhằm nâng cao tính đa dạng dữ liệu. Thứ ba, mở rộng đánh giá trên nhiều kiến trúc mạng cốt lõi và bộ dữ liệu thực tế đa dạng hơn để kiểm chứng tính ổn định và khả năng tổng quát. Cuối cùng, nghiên cứu chiến lược tinh chỉnh nhãn giả hiệu quả hơn nhằm tăng cường hiệu năng trong huấn luyện không giám sát.

14. Các công trình đã công bố có liên quan đến luận án: Anh D. Nguyen, Dang H. Pham

, and Hoa N. Nguyen, “GAN-based Data Augmentation and Pseudo-Label Refinement for Unsupervised Domain Adaptation Person Re-Identification”, ICCCI 2023 – 15th International Conference on Computational Collective Intelligence.

https://doi.org/10.1007/978-3-031-41456-5_45 . (WoS, Scopus). Dang H. Pham

, Anh D. Nguyen, Long V. Vu and Hoa N. Nguyen, “IQAGA: Image Quality Assessment-Driven Learning with GAN-Based Dataset Augmentation for Cross-Domain Person Re-Identification”, SOICT 2023 – 12th International Symposium on Information and Communication Technology.

https://doi.org/10.1145/3628797.3628961 . (WoS, Scopus). Dang H. Pham

, Anh D. Nguyen and Hoa N. Nguyen, “GAN-based Data Augmentation and Pseudo-Label Refinement with Holistic Features for Unsupervised Domain Adaptation Person Re-Identification”, Journal of Knowledge-Based Systems, Elsevier.

https://doi.org/10.1016/j.knosys.2024.111471 . (SCI-E, Q1-Scopus). Dang H. Pham

and Hoa N. Nguyen “SCM-ReID: Enhancing Person Re-Identification by Supervised Contrastive-Metric Learning and Hybrid Loss Optimization”, Journal of Electronic Imaging.

https://doi.org/10.1117/1.JEI.34.4.043001. (SCI-E, Q3-Scopus) Dang H. Pham

, Tu N. Nguyen, Hoa N. Nguyen “ViTC-UReID: Enhancing Unsupervised Person ReID with Vision Transformer Image Encoder and Camera-Aware Proxy Learning”, Journal of Computer Science and Cybernetics. (Accepted)