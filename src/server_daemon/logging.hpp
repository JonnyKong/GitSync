#include <stdio.h>
#include <stdarg.h>     /* va_list, va_start, va_arg, va_end */

void verbose(const char * fmt, ... ) {
  va_list args;  /* Used as a pointer to the next variable argument. */
  va_start(args, fmt);  /* Initialize the pointer to arguments. */

  #ifndef NDEBUG
  vprintf(fmt, args);
  #endif
  va_end(args);
}