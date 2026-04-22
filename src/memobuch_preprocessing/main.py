from memobuch_preprocessing.MemorProcessor import MemoProcessor


def main():
    memo_processor = MemoProcessor()
    memo_processor.load_data()
    memo_processor.output_data()
    memo_processor.output_person_list_object()