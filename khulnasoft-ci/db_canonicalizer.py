#!/usr/bin/env python

##################################################################
"""
Given two Postgres DDL files, compare them and determine whether they
are "the same" or "different".

Two DDL files are judged to be the same if they contain exactly the same
set of statements of the following kind:
    ALTER
    COMMENT
    CREATE EXTENSION
    CREATE INDEX
    CREATE SCHEMA
    CREATE SEQUENCE
    CREATE TABLE
    CREATE TYPE
    SELECT
    SET

(Yes, SELECT (others too?) is DML, not DDL.)

Comparison is done by:
A. For each DDL file
    1. Parse it with sqlparse, splitting individual statements into
       elements of an array
    2. Iterate over the array, storing each statement from the list
       above into a hashtable, like:

       all_stmts {
        "ALTER": [
            "ALTER TABLE ADD...",
            "ALTER...",
            ...
        ],
        "COMMENT": [
            "COMMENT ON COLUMN ...",
            "COMMENT ON TABLE ...",
            ...
        ],
        ...
       }
B. Compare the two hashtables
    1. They're the same: exit with success
    2. They differ
        a. Convert each to a python set
        b. Do set difference on them, printing out what differs
        c. exit with failure

See the shell functions db-diff-install() and diff-db-versions() in 
the file common_tasks in this repo to see how it's used (it's expected
that the functions are called by make in a target used to do schema
diffing; see the enterprise repo Makefile for an example).

db-diff-install()
    stands up a k8s cluster (specific to enterprise)

diff-db-version()
    helm installs the "first" version of enterprise to compare,
    dumps the schema to a file, uninstalls it, helm installs the
    "second" version of enterprise to copmare, dumps the schema to
    a file, brings down the cluster, and then runs this canonicalizer
    code on the two dumped schema files
"""
##################################################################

from datetime import datetime
import logging
import sys

import sqlparse


def make_logger(name="db_canonicalizer", log_dir = ".", quiet=False, nologging=False):

    logger = logging.getLogger(name)

    logging.FAIL = 70

    logging.addLevelName(logging.FAIL, 'FAIL')
    setattr(logger, 'fail', lambda message, *args: logger._log(logging.FAIL, message, args))

    logger.setLevel(logging.DEBUG)
    logformat = logging.Formatter("%(asctime)s | %(levelname)s | %(threadName)s | %(message)s")

    if not quiet:
        streamhandler = logging.StreamHandler(sys.stdout)
        streamhandler.setLevel(logging.INFO)
        streamhandler.setFormatter(logformat)
        logger.addHandler(streamhandler)
    if not nologging:
        filehandler = logging.FileHandler("{}/{}-{}.log".format(log_dir, name, datetime.now().strftime("%Y-%m-%d-%H%M-%S")), "w")
        filehandler.setLevel(logging.DEBUG)
        filehandler.setFormatter(logformat)
        logger.addHandler(filehandler)
    return logger


def canonicalize_ddl(ddl, log):

    alter = []
    comment = []
    create_extension = []
    create_index = []
    create_schema = []
    create_sequence = []
    create_table = []
    create_type = []
    select = []
    sets = []
    all_stmts = { "alter": alter,
                  "comment": comment,
                  "create_extension": create_extension,
                  "create_index": create_index,
                  "create_schema": create_schema,
                  "create_sequence": create_sequence,
                  "create_table": create_table,
                  "create_type": create_type,
                  "select": select,
                  "sets": sets
    }

    # Note that a regex (e.g., ^CREATE TABLE) to detect start of line would be
    # good, but with the way the DDL file is generated and the way sqlparse
    # parses it we're pretty safe.
    statements = sqlparse.split(ddl)
    for stmt in statements:
        if stmt.startswith("ALTER"):
            alter.append(stmt)
        elif stmt.startswith("COMMENT"):
            comment.append(stmt)
        elif stmt.startswith("CREATE EXTENSION"):
            create_extension.append(stmt)
        elif stmt.startswith("CREATE SEQUENCE"):
            create_sequence.append(stmt)
        elif stmt.startswith("CREATE SCHEMA"):
            create_schema.append(stmt)
        elif stmt.startswith("CREATE TABLE"):
            create_table.append(stmt)
        elif stmt.startswith("CREATE TYPE"):
            create_type.append(stmt)
        elif (stmt.startswith("CREATE INDEX") or stmt.startswith("CREATE UNIQUE INDEX")):
            create_index.append(stmt)
        elif stmt.startswith("SELECT"):
            select.append(stmt)
        elif stmt.startswith("SET"):
            sets.append(stmt)
        else:
            log.debug("Unknown statement: {}".format(stmt))

    return all_stmts


def compare_ddl_files(old, new):
    log = make_logger()
    old_stmts = canonicalize_ddl(open(old), log)
    new_stmts = canonicalize_ddl(open(new), log)

    if old_stmts == new_stmts:
        log.debug("Canonicalized DDL is the same.")
        sys.exit(0)

    # Ohnoes. Look at each statement type and see where they differ.
    for stmt_type in [ "alter", "comment", "create_extension", "create_index",
                       "create_schema", "create_sequence", "create_table",
                       "create_type", "select", "sets" ]:

        old_set = set(old_stmts[stmt_type])
        new_set = set(new_stmts[stmt_type])

        if old_set == new_set:
            log.debug("{}: Statements equal.".format(stmt_type))
            continue

        log.fail("{}: In old DDL but not new: {}".format(stmt_type, old_set.difference(new_set)))
        log.fail("{}: In new DDL but not old: {}".format(stmt_type, new_set.difference(old_set)))

    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Args should include old DDL file and new DDL file, relative to pwd.")
        sys.exit(1)

    compare_ddl_files(sys.argv[1], sys.argv[2])
