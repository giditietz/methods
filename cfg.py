import random
import re
from collections import defaultdict
import string
from itertools import product
from z3 import *
from os import path
from time import clock


# rrandom.seed(1)


#
# def parse(base):
#     pos = 0
#     x = base.split()
#     if x[0] == 'And':




class CFG(object):
    def __init__(self):
        self.main_productions = defaultdict(list)
        self.tail_productions = defaultdict(list)
        self.special_derivations = []

    def state_special_derivations(self, nonterminals):
        '''
        Creates a list that contains all nonterminals that are used in both queries: the regular one and the z3 one.
        :param nonterminals: a list of nonterminals whose derivations are different in the 2 query types
        '''
        self.special_derivations.extend(nonterminals)

    def add_main_prod(self, lhs, rhs):
        """ Add a main production to the grammar. 'rhs' can
            be several productions separated by '|'.
            Each production is a sequence of symbols
            separated by whitespace.

            Usage:
                grammar.add_prod('NT', 'VP PP')
                grammar.add_prod('Digit', '1|2|3|4')
        """
        prods = rhs

        for prod in prods:
            self.main_productions[lhs].append(tuple(prod.split()))

    def add_prod(self, lhs, rhs):
        """ Add a tail production to the grammar. 'rhs' can
            be several productions separated by '|'.
            Each production is a sequence of symbols
            separated by whitespace.

            Usage:
                grammar.add_prod('NT', 'VP PP')
                grammar.add_prod('Digit', '1|2|3|4')
        """
        prods = rhs
        for prod in prods:
            self.tail_productions[lhs].append(tuple(prod.split()))

    def gen_intermediate_form(self, symbol):
        """ given a symbol from the tail production (Token -> do something)
            generate a condition, E.G. Token -> `year' <= '1994'
                                       Token -> starts(`name', "F")
        """
        sentence = ''

        # select one production of this symbol randomly
        rand_prod = random.choice(self.tail_productions[symbol])
        for sym in rand_prod:
            # for non-terminals, recurse
            if sym in self.tail_productions:
                if sym not in self.special_derivations:
                    sentence += self.gen_intermediate_form(sym)
                else:
                    sentence += sym + ' '
            else:
                sentence += sym + ' '

        return sentence

    def gen_random(self, symbol, max_hight=2):
        """ Generate a random base sentence from the
            main grammar, starting with the given
            symbol.

            output example : (E or (E and not(E)))
                             (not(E) or not(E and not(E)))
        """
        sentence = ''
        # select one production of this symbol randomly
        rand_prod = random.choice(self.main_productions[symbol])
        if max_hight > 0:
            for sym in rand_prod:
                # for non-terminals, recurse
                if sym in self.main_productions:
                    sentence += self.gen_random(sym, max_hight - 1)
                else:
                    sentence += sym + ' '
        else:
            sentence += 'TOKEN' + ' '
        return sentence

    def gen_random_terminal(self, symbol, max_hight=2):
        query = ''
        base = CFG.gen_random(self, symbol, max_hight)

        for tok in base.split():
            if tok in self.tail_productions:
                query += self.gen_intermediate_form(tok)
            else:
                query += tok + ' '

        return query

    def create_both_queries(self, intermediate_form, genre_map, syllable_map):
        sentence1 = ''
        sentence2 = ''

        # select one production of this symbol randomly
        for sym in intermediate_form.split():
            # for non-terminals,
            if sym in self.tail_productions:
                choise = random.choice(self.tail_productions[sym])[0]
                sentence1 += choise
                if 'genre' in sym.lower():
                    sentence2 += genre_map[choise]
                if 'text' in sym.lower():
                    sentence2 += syllable_map[choise]

            else:
                sentence1 += sym + ' '
                sentence2 += sym + ' '

        return sentence1, sentence2


def generate_random_query(max_hight=2):
    """
    Simulates an improved CFG logic to generate random queries.
    There are two parts:
        1.) generate the 'base' of the query,
                E.G. (E) and ((E) or not(E))
        2.) generate the condition for each expression (E).
                E.G. (`rank`!="514")and((`running_time_secs`<="10020")or(not(contains(`actors`,"di"))))

        The maximum hight of the derivation tree of the 'base' is limited by 'max_hight'.
        After 'max_hight' is reached, the final 'base' query will be derived into its final form (#2).

    :param max_hight: maximal hight of derivation tree
    :return: a valid query (string)
    """
    cfg = CFG()

    # TODO - create a function that extract the variables from the rules
    textual_fields_names = ['title', 'actor', 'country', 'director']
    textual_operators_names = ['starts', 'contains', 'ends']
    years = ['{0}'.format(x) for x in range(1890, 2017, 5)]
    lengths = ['{0}'.format(x) for x in range(3600, 12600, 600)]
    ratings = ['{0}'.format(x / 100.0) for x in range(0, 1000, 33)]

    ### genres ###
    genres_list = ['"Action"', '"Crime"', '"Comedy"',
                   '"Horror"', '"Drama"', '"Animation"',
                   '"Music"', '"Biography"', '"Adventure"',
                   '"Sci-Fi"', '"Documentary"', '"Mystery"',
                   '"Musical"', '"Thriller"', '"Family"',
                   '"Film-Noir"', '"Sport"', '"Romance"', '"War"',
                   '"Western"', '"Fantasy"', '"History"']

    genres_id_map = {genres_list[i]: i for i in xrange(len(genres_list))}
    genres_sets = ['genres in ({0})'.format(s) for s in
                   [', '.join([random.choice(genres_list) for _ in xrange(3)]) for _ in xrange(100)]]
    genres_map = dict()
    for g_set in genres_sets:
        cur_genres = [gen.strip() for gen in re.split(r'[,; ()]+', g_set)[2:]]
        z3_format_genres = r'Or(genre=={0},genre=={1},genre=={2})'.format(genres_id_map[cur_genres[0]],
                                                                          genres_id_map[cur_genres[1]],
                                                                          genres_id_map[cur_genres[2]])
        genres_map[z3_format_genres] = g_set

    genres_perms = genres_map.keys()

    ### textual fields ###
    syllable_list = [r'"{0}{1}"'.format(x[0], x[1]) for x in
                     set(product(string.ascii_lowercase, 'aeoiu')).union(
                         set(product('aeoiu', string.ascii_lowercase)))]
    syllable_id_map = {syllable_list[i]: i for i in xrange(len(syllable_list))}
    syllable_map = dict()
    for syllable in syllable_list:
        textual_field = random.choice(textual_fields_names)
        textual_operator = random.choice(textual_operators_names)
        z3_format_titles = r'{0}_{1}_syllable=={2}'.format(textual_operator, textual_field, syllable_id_map[syllable])
        syllable_map[z3_format_titles] = "{0}({1},{2})".format(textual_operator, textual_field, syllable)
    syllables = syllable_map.keys()

    ### Derivation rules ###
    cfg.add_main_prod('E', ['And ( E , E )', 'Or ( E , E )', 'Not ( E )', 'TOKEN'], )
    cfg.add_prod('TOKEN', ['NUMERAL_FIELD', 'TEXTUAL_FIELD'])
    cfg.add_prod('OP1', ['>=', '<=', '==', '!='])
    cfg.add_prod('OP2', ['>=', '<='])  # No '==' since it will limit the query
    cfg.add_prod('NUMERAL_FIELD', ['YEAR', 'LENGTH', 'RATING'])  # No '==' since it will limit the query
    cfg.add_prod('TEXTUAL_FIELD', ['GENRES_IN', 'TEXT_OP'])
    cfg.add_prod('YEAR', ['year OP2 YEAR_RANGE'])  # No '==' since it will limit the query
    cfg.add_prod('YEAR_RANGE', years)
    cfg.add_prod('LENGTH', ['movie_length OP2 LENGTH_RANGE'])
    cfg.add_prod('LENGTH_RANGE', lengths)
    cfg.add_prod('RATING', ['rating OP2 RATING_RANGE'])
    cfg.add_prod('RATING_RANGE', ratings)
    cfg.add_prod('GENRES_IN', genres_perms)
    cfg.add_prod('TEXT_OP', syllables)
    cfg.state_special_derivations(['GENRES_IN', 'TEXT_OP'])

    base_query = cfg.gen_random_terminal('E', max_hight)
    final_z3_query, final_real_query = cfg.create_both_queries(base_query, genres_map, syllable_map)

    final_z3_query = final_z3_query.replace(" ", "")  # beautify
    final_mock_query = final_real_query.replace(" ", "").replace("genresin", "genres in")  # beautify
    return final_z3_query, final_mock_query


def main():
    running = True
    ###Declare z3 vars:
    year = Int('year')
    movie_length = Int('length')
    rating = Real('rating')
    genre = Int('genre')
    starts_title_syllable = Int('starts_title_syllable')
    starts_actor_syllable = Int('starts_actor_syllable')
    starts_country_syllable = Int('starts_country_syllable')
    starts_director_syllable = Int('starts_director_syllable')
    contains_title_syllable = Int('contains_title_syllable')
    contains_actor_syllable = Int('contains_actor_syllable')
    contains_country_syllable = Int('contains_country_syllable')
    contains_director_syllable = Int('contains_director_syllable')
    ends_title_syllable = Int('ends_title_syllable')
    ends_actor_syllable = Int('ends_actor_syllable')
    ends_country_syllable = Int('ends_country_syllable')
    ends_director_syllable = Int('ends_director_syllable')
    variables = [year, movie_length, rating, genre,
                 starts_title_syllable, starts_actor_syllable, starts_country_syllable, starts_director_syllable,
                 contains_title_syllable, contains_actor_syllable, contains_country_syllable,
                 contains_director_syllable,
                 ends_title_syllable, ends_actor_syllable, ends_country_syllable, ends_director_syllable]
    ### User interface ###
    print("Welcome to the random query generator demo!")
    print(
    "Please choose:\n1 - show a random SAT query\n2 - show a random UNSAT query\n3 - create a dataset\n4 - quit\n")
    while running:
        user = raw_input("Your input:\n")
        if user == '1' or user == '2':
            while True:
                if user == '1':
                    comp = sat
                if user == '2':
                    comp = unsat
                z3_query, real_query = generate_random_query(3)
                s = Solver()
                s.add(Exists(variables, eval(z3_query)))
                res = s.check()
                if res == comp:
                    print(
                    "\nZ3 Query: {0}\nReal Query: {1}\nResult: {2}\n".format(z3_query, real_query, str(res).upper()))
                    break

        elif user == '3':
            entries_dict = defaultdict(int)
            entries_dict[2000] = 0
            max_hight = 20
            unsats = 0
            sats = 0
            index = 0
            use_file = False
            runs = int(raw_input("Please choose the size of the dataset:\n"))
            if runs > 50:
                ask_for_file = raw_input("The chosen size is quite big - would you \n"
                                         "like to write it to a file for your convenience? [yes=1,no=0]\n")
                if ask_for_file == '1':
                    use_file = True
                    dir_path = os.path.dirname(__file__)
                    filepath = "query_demo_data.csv"
                    file = open(filepath, 'w+')
                    print("Data is being written to {0}/{1}.\n".format(dir_path, filepath))

            print("`Result` stands for SAT/UNSAT. 0 means SAT, 1 means UNSAT.")
            if use_file:
                file.write(
                    "{0}\t{1}\t{2}\t{3}\t{4}\t{5}\n".format("index", "result", "length", "bucket", "derivation_time",
                                                            "verification_time"))
            else:
                print("{0}\t{1}\t{2}\t{3}\t{4}\t{5}".format("index", "result", "length", "bucket", "derivation_time",
                                                            "verification_time"))
            while (index < runs):
                window_size = 30
                derive_start = clock()
                query, _ = generate_random_query(max_hight)
                derive_end = clock()
                derivation_t = derive_end - derive_start
                sorted_key_list = sorted(entries_dict.keys())
                for key in sorted_key_list:
                    if entries_dict[key] != window_size:
                        limit = int(key)
                        break
                if (len(query) < limit): #todo - dynamic blocking
                    continue  # short queries are not interesting
                year = Int('year')
                length = Int('length')
                vars = [year, length]
                s = Solver()
                s.add(Exists(vars, eval(query)))
                verify_start = clock()
                res = s.check()
                verify_end = clock()
                verification_t = verify_end - verify_start
                bucket = (len(query) / 1000) * 1000
                if entries_dict[bucket] < window_size:
                    if (res == unsat):
                        unsats += 1
                        res = 1
                    elif (res == sat):
                        sats += 1
                        res = 0

                    if use_file:
                        file.write("{0}\t\t{1}\t\t{2}\t{3}\t{4}\t{5}\n".format(index, res, len(query), bucket, derivation_t,
                                                                               verification_t))
                    else:
                        print("{0}\t\t{1}\t\t{2}\t{3}\t{4}\t{5}".format(index, res, len(query), bucket, derivation_t,
                                                                        verification_t))
                    index += 1
                    entries_dict[bucket] += 1

            print("\nSummary:\n\tSATS:{0}\tUNSATS:{1}\n".format(sats, unsats))
            if use_file:
                file.close()
        elif user == '4':
            print("Goodbye, we hope you've enjoyed the demo!\n")
            running = False
        else:
            print("Invalid argument. Please try again.\n")


if __name__ == '__main__':
    main()
