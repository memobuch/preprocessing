from memobuch_preprocessing.MemoProcessor import MemoProcessor


def main():
    memo_processor = MemoProcessor()
    memo_processor.load_data()
    memo_processor.output_data()