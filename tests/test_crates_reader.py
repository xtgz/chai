import json
import pytest
from src.reader.crates.reader import CratesReader
from src.reader.reader import DEFAULT_BATCH_SIZE


@pytest.fixture
def crates_reader() -> CratesReader:
    return CratesReader()


def test_packages(crates_reader: CratesReader, capsys):
    crates_reader.packages()
    captured = capsys.readouterr()
    assert captured.out != "", "no output was found"

    try:
        json_output = json.loads(captured.out)
        assert isinstance(json_output[0], dict), "not a list of dictionaries"
        assert len(json_output[0]) == 3, "not 3-item dictionaries"
        assert (
            len(json_output) > 0 and len(json_output) <= DEFAULT_BATCH_SIZE
        ), "invalid batch size"
    except json.JSONDecodeError:
        print(len(captured.out))
        pytest.fail("output is not valid JSON")


# def test_file_reading_and_batch_size(crates_reader):
#     with patch("builtins.open", new_callable=mock_open) as mock_file, patch(
#         "src.reader.crates.reader.Reader.finder"
#     ) as mock_finder, patch("src.reader.crates.reader.Reader.output") as mock_output:
#         for file_type, file_name in crates_reader.files.items():
#             mock_finder.return_value = f"/path/to/{file_name}"

#             # Create mock data with 25,000 rows
#             mock_data = "\n".join([",".join(["data"] * 10) for _ in range(25000)])
#             mock_file.return_value.__enter__().read.return_value = mock_data

#             # Call the corresponding method
#             getattr(crates_reader, file_type)()

#             # Check if the correct file was read
#             mock_finder.assert_called_with(file_name)

#             # Check if output was called 3 times (2 full batches, 1 partial)
#             assert mock_output.call_count == 3

#             # Check batch sizes
#             assert len(mock_output.call_args_list[0][0][1]) == 10000
#             assert len(mock_output.call_args_list[1][0][1]) == 10000
#             assert len(mock_output.call_args_list[2][0][1]) == 5000

#             # Reset mocks for next iteration
#             mock_output.reset_mock()
#             mock_finder.reset_mock()


# @pytest.mark.parametrize("batch_size", [1000, 5000, 10000, 50000])
# def test_performance_with_different_batch_sizes(crates_reader, batch_size):
#     start_time = time.time()

#     with patch("src.reader.crates.reader.Reader.output") as mock_output:
#         # Create mock data with 100,000 rows
#         mock_data = [{"key": "value"} for _ in range(100000)]

#         # Process data in batches
#         for i in range(0, len(mock_data), batch_size):
#             batch = mock_data[i : i + batch_size]
#             crates_reader.output(None, batch)

#     end_time = time.time()
#     duration = end_time - start_time
#     print(f"\nBatch size {batch_size}: {duration:.4f} seconds")


# def test_output_format(crates_reader):
#     with patch("src.reader.crates.reader.Reader.output") as mock_output:
#         crates_reader.packages()

#         # Check if the output is a list of dictionaries
#         assert isinstance(mock_output.call_args[0][1], list)
#         assert all(isinstance(item, dict) for item in mock_output.call_args[0][1])
