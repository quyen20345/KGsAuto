# Độc đáo với hệ thống hỗ trợ nâng cao chất lượng văn bản

- ID: 9233
- Date: 2017-11-22T08:46:10
- URL: https://uet.edu.vn/doc-dao-voi-thong-ho-tro-nang-cao-chat-luong-van-ban/
- Categories: Tin Tổng Hợp
- Tags: 

## Content

Với mục đích nâng cao chất lượng của các đồ án, khóa luận, luận văn của người học nói riêng và chất lượng giáo dục và đào tạo nói chung, nhóm tác giả của trường ĐH Công nghệ – ĐHQGHN đã xây dựng một hệ thống trực tuyến hỗ trợ kiểm tra lỗi chính tả và kiểm tra trùng lặp của các văn bản.

Sự phát triển của công nghệ thông tin đã mang lại nhiều đột phá trong cuộc sống của con người. Trong lĩnh vực giáo dục, máy tính và Internet đã giúp cho người dạy và người học tiếp cận được nhiều nguồn thông tin, nhiều công cụ phục vụ cho việc dạy và học.

Hiện nay, nhiều trường đại học trên thế giới đang sử dụng một số hệ thống ứng dụng để hỗ trợ cho việc kiểm tra và đánh giá văn bản được tạo ra bởi người học (bao gồm các bài tập lớn cho đến các đồ án, khóa luận, luận văn,…). Những hệ thống như vậy thường có các chức năng kiểm tra lỗi chính tả, ngữ pháp, và định dạng của văn bản và chức năng kiểm tra xem nội dung của văn bản có trùng với nội dung của một tài liệu nào đã được công bố trước đó hay không (chống sao chép). Tuy nhiên các hệ thống này chủ yếu phục vụ cho các tài liệu viết bằng tiếng Anh và có thu phí sử dụng khá cao.

PGS.TS Phạm Bảo Sơn (thứ 2 từ trái sang) đại diện nhóm tác giả nhận giải nhì lĩnh vực CNTT tiềm năng của Giải thưởng Nhân tài Đất Việt 2017

Xuất phát từ thực tế đó, DoIT – Hệ thống hỗ trợ nâng cao chất lượng văn bản ra đời với sự tham gia của 9 thành viên của ĐH Công nghệ – ĐHQGHN, trong đó có sự tham gia của PGS.TS Phạm Bảo Sơn – Phó Hiệu trưởng Nhà trường.

DoIT gồm hai tính năng cơ bản là kiểm lỗi chính tả và phát hiện trùng lặp cho tài liệu tiếng Việt. Hệ thống có thể xử lý các tài liệu ở phần lớn các định dạng phổ biến hiện nay như doc, docx, pdf, ppt, … Với chức năng kiểm lỗi chính tả, DoIT ngoài việc chỉ ra các từ bị lỗi còn đề xuất từ đúng thay thế. Chức năng phát hiện trùng lặp sẽ chỉ ra phần trùng trong văn bản được kiểm tra với các phần của các tài liệu có trong cơ sở dữ liệu (CSDL) của hệ thống. Có ba mức trùng lặp gồm cao, thấp, và trung bình và được thể hiện bằng ba màu. Người dùng có thể chia sẻ, gửi tài liệu qua hệ thống.

DoIT vừa vinh dự nhận Giải nhì lĩnh vực CNTT tiềm năng của Giải thưởng Nhân tài Đất Việt 2017. Vậy hai tính năng của DoIT có gì độc đáo?

Tính năng kiểm lỗi chính tả

Chức năng kiểm lỗi chính tả được chia làm hai chức năng nhỏ hơn là: phát hiện lỗi và sửa lỗi. Lỗi chính tả trong Tiếng Việt được chia thành 2 loại chính: âm tiết sai chính tả không tồn tại trong từ điển Tiếng Việt và âm tiết sai chính tả do ngữ cảnh. Trong sản phẩm này, này chúng tôi chủ yếu tập trung vào phần âm tiết sai chính tả do ngữ cảnh. Những âm tiết này tồn tại trong từ điển Tiếng Việt nhưng không phù hợp với văn bản (Ví dụ: trong câu “Cuốn xách này rất hay”, từ “xách” mang ý nghĩ là mang, vác theo đã bị dùng sai, từ chính xác cần được dùng ở đây là từ “sách”).

Mô hình ngôn ngữ N-gram là hướng tiếp cận chính và kèm theo đó là phân đoạn từ (word segmentation), khoảng cách Levenstein để hỗ trợ đánh giá ứng viên tốt nhất. Mô đun sẽ gồm các bước tiền xử lý, sinh tập âm tiết nhầm lẫn, và đánh giá ứng viên phù hợp. Với bước tiền xử lý, mô đun tiến hành loại bỏ các thành phần gây nhiễu trong câu và tách câu thành các từ riêng biệt. Việc này sẽ xóa đi các dấu câu không cần thiết cũng như các ký hiệu đặc biệt đồng thời gán nhãn cho các cụm ký tự đặc biệt như số, ngày tháng, … Bước này giúp mô đun hạn chế được sai sót và nhầm lẫn khi sửa lỗi, tăng độ chính xác cũng như hiệu suất hoạt động. Bước tiếp theo là tạo tập âm tiết nhầm lẫn. Tập nhầm lẫn của âm tiết s là tập bao gồm các âm tiết có có mối quan hệ về chính tả với s. Tập này được xây dựng dựa trên các lỗi chính tả thường thấy, bao gồm có: lỗi do đánh máy sai (“ddi” – “đi”), lỗi âm đầu (“xách” – “sách”), lỗi âm cuối (“bắt buột” – “bắt buộc”), lỗi dấu (“khiếm tốn” – “khiêm tốn”) và lỗi từ địa phương (“khiếm” – “khím”).

Nhóm tác giả của DoIT gồm các gương mặt còn rất trẻ

Để tạo được tập nhầm lẫn của âm tiết, mô đun sẽ phân tích cấu trúc của từ theo chuẩn cấu trúc của ngữ pháp tiếng Việt. Dựa trên việc phân tích này, các ứng viên được tạo dựa trên việc thay thế từng thành phần với những thành phần thay thế có khả năng, bao gồm âm đầu, âm cuối và thanh sắc. Đối với lỗi do đánh máy, các ứng viên sẽ được tạo ra từ việc tương tác với từng ký tự thông qua ba thao tác: chèn, xóa và thay thế. Để giảm kích thước của tập nhầm lẫn, mô đun sử dụng từ điển Tiếng Việt và tần suất xuất hiện của âm tiết như một công cụ đắc lực. Việc này sẽ làm giảm đáng kể số lượng các âm tiết không phù hợp. Bước cuối cùng trong quá trình xử lý của mô đun là đánh giá ứng viên phù hợp.

Tính năng phát hiện trùng lặp

Việc tìm kiếm các tài liệu tương tự về nội dung được dựa trên hệ thống Apache Solr và dùng thêm độ đo tương đồng Cosine. Độ đo Cosine đánh giá sự tương đồng của hai chuỗi ký tự bằng việc chuyển hai chuỗi ký tự đó thành hai vector trong không gian dựa trên tần suất xuất hiện của các từ riêng biệt trong hai câu. Độ tương đồng giữa hai chuỗi ký tự được xác định là cosine góc giữa hai vector tương ứng.

Độ đo tương tự Cosine có một hạn chế đó là độ đo này không quan tâm đến thứ tự của các từ trong hai chuỗi ký tự. Vì vậy, nếu hai chuỗi ký tự được kiểm tra chứa các từ giống hệt nhau chỉ khác nhau về thứ tự thì độ đo Cosine vẫn sẽ cho kết quả điểm tương tự lớn nhất là 1.

Một điểm sáng tạo khác của DoIT là dựa vào đặc điểm về cấu trúc chung của các khóa luận, luận văn, luận án, hệ thống sẽ không kiểm tra sự trùng lặp với các thành phần ít đóng góp vào nội dung văn bản như các siêu dữ liệu (meta-data, ví dụ tiêu đề, tác giả), tài liệu tham khảo, lời cảm ơn, mục lục. Đơn vị được sử dụng để tính toán độ trùng lặp là câu. Trong trường hợp có sự trùng lặp của các câu liền nhau, các câu này sẽ được nối với nhau để thể hiện mức độ tương đồng cao giữa hai văn bản.

Thêm vào đó, DoIT sử dụng chiến thuật tìm kiếm theo bước. Với một văn bản nhiều câu, thay vì tuần tự kiểm tra sự trùng lặp của từng câu trong văn bản đó với các câu trong CSDL, hệ thống sẽ xác định các câu sẽ được kiểm tra trùng lặp theo kết quả kiểm tra của câu trước. Cụ thể, sau khi kiểm tra câu thứ

i, nếu câu này có độ tương đồng cao với một câu trong CSDL, các câu i-1 và i+1 sẽ được kiểm tra. Ngược lại, nếu câu thứ i có mức độ trùng lặp thấp, câu tiếp theo được kiểm tra sẽ là i+3 . Chiến thuật này sẽ giúp hệ thống giảm thời gian xử lý văn bản (đặc biệt các văn bản ít trùng lặp với CSDL).

CSDL của DoIT được bổ sung thường xuyên và theo định hướng của người dùng. Người quản trị hệ thống có thể thêm các nguồn dữ liệu từ Internet bằng cách chỉ ra URL của nguồn dữ liệu. Hệ thống sẽ thu thập (crawl) và đánh chỉ mục vào CSDL phục vụ cho việc kiểm tra trùng lặp. Ngoài ra, người dùng thông thường có thể đề xuất các nguồn dữ liệu nên được đưa vào CSDL để kiểm tra.

Thêm vào đó, hệ thống còn trích xuất các URL chứa trong các tài liệu được người dùng tải lên và xem đây là những nguồn dữ liệu tiềm năng. Quản trị hệ thống sẽ được thông báo về những nguồn này và quyết định có hay không đưa nguồn dữ liệu vào CSDL của hệ thống.

Hiện tại DoIT đang được triển khai áp dụng tại Đại học Quốc gia Hà Nội, với khoảng 3.000 người dùng và khoảng 7.000 tài liệu trong cơ sở dữ liệu để kiểm tra sự trùng lặp. Người dùng của hệ thống phần lớn từ các đơn vị thành viên của ĐHQGHN và các trường Đại học Thủy lợi, Học viện Công nghệ Bưu chính Viễn thông, Đại học Thái Nguyên…

Sản phẩm DoIT được cung cấp trên nền web, giúp người dùng có thể sử dụng ở bất kỳ thiết bị nào, miễn là có kết nối Internet. Bạn đọc có thể trải nghiệm sản phẩm tại

http://doit.uet.vnu.edu.vn hoặc tại http://doit.lic.vnu.edu.vn . Theo Nguyễn Hùng (Báo điện tử Dân trí)