# methods

Running the project:
In order to run the project you must have z3 installed. The easiest way is to use the "softprod" VM (the VM that we used for 
Dafny, CBMC,KLEE etc.).

When you run the demo, an interactive prompt starts and 4 options ar offered:
1 - get a SAT query
    The demo will return the first random SAT query it finds.
    
2 - get a UNSAT query
    The demo will return the first random UNSAT query it finds (Might take up to a second). 
    
3 - create a data set
    The demo will ask you for a size. If the size is bigger than 50, the demo will ask you if you want to write the data to a     file. 
    Then the demo will create random queries 'size' times.
    This option is for statistical analysis of queries.

4 - quit
    Will quit the demo 
