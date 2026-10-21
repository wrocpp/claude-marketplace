// Qt registers the metatype of a pointer to a class under className() + "*", and in a debug build aborts on a name
// it would normalize differently. A compiler spells a template specialization its own way (GCC: "unsigned int", a
// space in "> >", one after a comma); Qt wants "uint", ">>" and no space. A class name, a metatype name or a
// signal argument type must be in Qt's form, so run any name you build by hand through QMetaObject::normalizedType.
#include "../check.hpp"

#include <QtCore/QCoreApplication>
#include <QtCore/QMetaObject>
#include <QtCore/QMetaType>

#include <csignal>
#include <cstdio>
#include <sys/wait.h>
#include <unistd.h>

namespace {
struct Spelling {
  const char* compiler;  // the way a compiler writes it
  const char* qt;        // what QMetaObject::normalizedType returns
};
constexpr Spelling kSpellings[] = {
    {"A<B<int> >", "A<B<int>>"},
    {"A<B<C<int> > >", "A<B<C<int>>>"},
    {"A<B<int> >*", "A<B<int>>*"},
    {"A<unsigned int>", "A<uint>"},
    {"A<unsigned>", "A<uint>"},
    {"A<unsigned long>", "A<ulong>"},
    {"A<unsigned long long>", "A<qulonglong>"},
    {"A<long long>", "A<qlonglong>"},
    {"A<unsigned short>", "A<ushort>"},
    {"A<unsigned char>", "A<uchar>"},
    {"QHash<unsigned int, Sample>", "QHash<uint,Sample>"},
    {"ns::A<QList<ns::B> >", "ns::A<QList<ns::B>>"},
    {"A<int, QList<unsigned int> >", "A<int,QList<uint>>"},
    {"A<int>", "A<int>"},
};

struct Plain {};

#ifndef QT_NO_DEBUG
// Runs `scenario` in a child process and reports whether it died of an assertion (SIGABRT).
template <class F>
bool aborts(F&& scenario) {
  std::fflush(nullptr);
  const pid_t child = fork();
  if (child == 0) {
    if (!std::freopen("/dev/null", "w", stderr)) _exit(2);
    scenario();
    _exit(0);
  }
  int status = 0;
  waitpid(child, &status, 0);
  return WIFSIGNALED(status) && WTERMSIG(status) == SIGABRT;
}
#endif
}  // namespace

int main(int argc, char** argv) {
  QCoreApplication app(argc, argv);
  for (const Spelling& s : kSpellings) {
    const QByteArray normalized = QMetaObject::normalizedType(s.compiler);
    if (normalized != s.qt) std::fprintf(stderr, "'%s': expected '%s', Qt gave '%s'\n", s.compiler, s.qt, normalized.constData());
    CHECK(normalized == s.qt);
  }
#ifndef QT_NO_DEBUG
  // The registration that aborts: a name Qt would normalize differently. The normalized spelling is accepted.
  CHECK(!aborts([] { qRegisterNormalizedMetaType<Plain*>("A<uint>*"); }));
  CHECK(aborts([] { qRegisterNormalizedMetaType<Plain*>("A<unsigned int>*"); }));
  CHECK(aborts([] { qRegisterNormalizedMetaType<Plain*>("A<B<int> >*"); }));
#else
  std::puts("SKIP the abort on a not normalized name (QT_NO_DEBUG: the assertion is compiled out)");
#endif
  return qt_cpp_test::finish("normalized_names");
}
