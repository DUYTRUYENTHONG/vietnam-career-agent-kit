# Fork kit và thử fine-tuning CV

Được tạo bởi **DUYTRUYENTHONG**, chia sẻ miễn phí cho cộng đồng.
Mã nguồn kit dùng MIT; Qwen và bản phái sinh có điều khoản riêng.
Xem [hướng dẫn lệnh đầy đủ](FINE_TUNING_START.md) và [danh mục mô hình](../models/README.md).

[Báo cáo thí nghiệm 8B với dữ liệu thật](REAL_DATA_PILOT_QA.md) chỉ công bố số
liệu tổng hợp. Huấn luyện đã hoàn thành nhưng chất lượng nội dung chưa đạt;
dữ liệu, câu trả lời gốc và trọng số vẫn được giữ riêng tư. Loss giảm không
chứng minh CV chính xác hơn hay tăng tỷ lệ được tuyển.

1. Fork trên GitHub, clone fork và chạy kiểm tra mã nguồn cùng toàn bộ unit test.
   Không cần Docker, Gmail hoặc trình duyệt để huấn luyện local.
2. Tạo môi trường Python riêng, cài đúng phiên bản trong hướng dẫn, tải mô hình
   công khai ra ngoài repo. Qwen3-0.6B dùng để kiểm tra quy trình; chất lượng viết
   CV của các thí nghiệm hiện tại chưa đạt yêu cầu.
3. Chạy demo với workspace dữ liệu giả mới. Review tự sinh chỉ là fixture kiểm
   thử, không dùng để phê duyệt CV thật.
4. Trong workspace thật: xác nhận thông tin có nguồn, nhập JD, đánh giá yêu cầu,
   review nội dung rồi `learning-export` và `learning-check`. Giữ nguyên giới hạn
   kinh nghiệm và mức hỗ trợ AI. Không đưa giấy tờ định danh hay CV tham khảo vào tập học.
5. Tách train/holdout theo công việc, dự án và nội dung gần trùng. Hai nhóm chỉ đủ
   chia tập, chưa chứng minh dữ liệu đủ hoặc không rò rỉ.
6. Huấn luyện LoRA vào thư mục mới, so sánh base/adapter trên cùng prompt holdout.
   Kiểm tra JSON, nguồn, ngữ cảnh, token và thời gian thực đo. Loss giảm không
   đồng nghĩa CV chính xác hơn hay tăng tỷ lệ được tuyển.
7. Chia sẻ mã nguồn và fixture giả qua PR đã qua QA. Adapter nghiên cứu cần model
   card, giấy phép, revision và checksum; dùng release asset cho trọng số. Giữ CV,
   tracker và mô hình học từ dữ liệu cá nhân ở workspace riêng theo mặc định.

Ba adapter 0.6B được công bố để nghiên cứu lỗi, chưa làm bộ viết CV mặc định.
Pilot 8B trong danh mục nghiên cứu đã chạy trên Colab nhưng tải về chưa được xác minh;
release không chứa trọng số 8B. Trạng thái dữ liệu/mô hình riêng của mỗi người dùng
phải được kiểm tra trong workspace của họ. Runner local hỗ trợ CPU/CUDA
LoRA, chưa triển khai QLoRA hay tự tải dữ liệu riêng lên Colab.

## Cập nhật dữ liệu thật

Khi có kinh nghiệm đã xác nhận, JD mới hoặc chỉnh sửa được review, dùng
[quy trình cập nhật có phiên bản](TRAINING_DATA_REFRESH.md) và
[prompt cho agent](../prompts/REFRESH_TRAINING_DATA.md). Đây là hướng dẫn dùng các
lệnh hiện có, không cài lịch chạy nền hay tự khởi động huấn luyện.

Giữ nguyên dataset và kết quả cũ. Đối chiếu nguồn, xử lý mâu thuẫn, cập nhật đánh
giá và review nội dung trước khi export vào thư mục mới. Không đưa CV tham khảo,
giấy tờ định danh hay chỉ số chưa xác nhận vào tập học. Khi ghép một bullet với
yêu cầu, chỉ đánh giá bằng chứng trong bullet đó; giữ rõ hỗ trợ AI, prototype,
thời gian dự án và tổng dữ liệu so với dữ liệu mỗi ngày.

Kiểm tra trùng lặp theo dự án và sự kiện nghề nghiệp ngoài cơ chế nhóm job/output
có sẵn. Nếu holdout cũ được đưa vào train, cần bộ đánh giá mới chưa dùng để học.
So sánh nội dung, nguồn và thời gian/token thực đo trước khi thay mô hình; loss
giảm chưa đủ. Email xác nhận gửi hồ sơ không phải nhãn CV tốt, im lặng không đồng
nghĩa bị từ chối. Dữ liệu và trọng số học từ thông tin cá nhân vẫn giữ riêng.
