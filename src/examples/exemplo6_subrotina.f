      PROGRAM TESTSUB
      INTEGER X
      X = 4
      CALL CUBO(X)
      END

      SUBROUTINE CUBO(N)
      INTEGER N, Q
      Q = N * N * N
      PRINT *, N, '** 3 =', Q
      RETURN
      END
