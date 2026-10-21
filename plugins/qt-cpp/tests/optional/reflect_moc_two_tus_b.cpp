#include "reflect_moc_class_template.hpp"

#include <QtCore/QMetaMethod>

namespace optional_fixture {
void add_from_second_unit(Container* container, const QHash<unsigned, int>& key) { container->add(key); }

const QMetaObject* meta_in_second_unit() { return &Container::staticMetaObject; }

int added_index_in_second_unit() { return QMetaMethod::fromSignal(&Container::added).methodIndex(); }

char const* signal_type_name_in_second_unit() {
  static Container* const none = nullptr;
  return typeid(none->added).name();
}
}  // namespace optional_fixture
