import unittest

def suite():
    modules_to_test = ("movegen","fen","eval", "zobrist", "frc_castling","bitboard") 
    tests = unittest.TestSuite()
    for module in map(__import__, modules_to_test):
        tests.addTest(unittest.findTestCases(module))
    return tests

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())

