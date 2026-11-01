# Fork kit và thử fine-tuning CV

Được tạo bởi **DUYTRUYENTHONG**, chia sẻ miễn phí cho cộng đồng.
Mã nguồn kit dùng MIT; Qwen và bản phái sinh có điều khoản riêng.
Xem [hướng dẫn lệnh đầy đủ](FINE_TUNING_START.md) và [danh mục mô hình](../models/README.md).

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
Pilot 8B đã chạy trên Colab nhưng tải về chưa được xác minh; release không chứa
trọng số 8B. Huấn luyện CV cá nhân chưa hoàn tất. Runner local hỗ trợ CPU/CUDA
LoRA, chưa triển khai QLoRA hay tự tải dữ liệu riêng lên Colab.
